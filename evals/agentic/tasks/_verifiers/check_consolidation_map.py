#!/usr/bin/env python3
"""Recompute a consolidation map's rows and counts from the supplied decisions.

The map's own "OK" lines and self-reported counts are never trusted: rows are
parsed out of the deliverable and compared with ``decisions.json``, and the
counts are re-derived from those rows.
"""
import json
import os
from pathlib import Path
import re
import sys

INPUTS = Path(os.environ.get('AGENTIC_INPUTS', '/inputs'))
VERBS = ('keep', 'new', 'absorb', 'merge-into', 'deprecate', 'retire')
ROW = re.compile(r'^- (' + '|'.join(VERBS) + r')\s+(\S.*)$')
COUNTS = re.compile(r'^Before (\d+) \| After (\d+) \| Net ([+-]?\d+)\b')
RECON_REMOVED = re.compile(r'^N\s*=\s*K\s*\+\s*X\s*\+\s*R\s*:\s*(\d+)\s*=\s*(\d+)\s*\+\s*(\d+)\s*\+\s*(\d+)\s+OK\s*$', re.I)
RECON_AFTER = re.compile(r'^M\s*=\s*K\s*\+\s*W\s*:\s*(\d+)\s*=\s*(\d+)\s*\+\s*(\d+)\s+OK\s*$', re.I)
COUNTS_DRAFT = re.compile(r'^Before (\d+) \| After (\S+) \| Net (\S+)')
NO_LOSS = re.compile(
    r'^(?:nothing|none|n/?a|not applicable|zero|lost nothing'
    r'|(?:no|without any)\s+(?:[\w-]+\s+){0,4}?(?:loss|lost|impact|regression))\b', re.I)
STOPWORDS = frozenset(
    'about after again all also already always another any are because been before being both but can could did '
    'does doing done down each else ever every for from had has have having here how into its just like made make '
    'many more most much must never not now off once one only other our out over own same she should since some '
    'still such than that the their them then there these they this those through too under until upon very was '
    'were what when where which while who why will with without would yet you your'.split())


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def expected_rows(decisions):
    """(verb, entity, target) for every decision, plus the unchanged keeps."""
    rows = []
    for unit in decisions['units']:
        for row in unit['rows']:
            rows.append((row['verb'], row['entity'], row.get('target', '')))
    rows += [('keep', name, '') for name in decisions.get('unchanged', [])]
    return rows


def parse_map(text):
    """Split into the counts line, `## ` sections and the rows each holds."""
    counts, sections, current = None, [], None
    for line in text.splitlines():
        found = COUNTS.match(line)
        if found and counts is None:
            counts = tuple(int(n) for n in found.groups())
        if line.startswith('## '):
            current = {'title': line[3:].strip(), 'rows': [], 'lines': []}
            sections.append(current)
            continue
        if current is None:
            continue
        current['lines'].append(line)
        row = ROW.match(line.strip())
        if row:
            verb, rest = row.groups()
            if verb == 'merge-into':
                pair = re.split(r'\s*(?:->|→)\s*', rest.strip())
                assert len(pair) == 2 and all(pair), 'merge-into rows read "<source> -> <target>"'
                current['rows'].append((verb, pair[0].strip(), pair[1].strip()))
            else:
                for name in rest.split(','):
                    name = name.strip()
                    if name:
                        current['rows'].append((verb, name, ''))
    return counts, sections


def field(section, label):
    for line in section['lines']:
        found = re.match(r'^' + re.escape(label) + r':\s*(\S.*)$', line.strip(), re.I)
        if found:
            return found.group(1)
    return ''


def section(sections, prefix):
    return [s for s in sections if s['title'].lower().startswith(prefix)]


def derived_counts(rows):
    verbs = [verb for verb, _, _ in rows]
    kept = sum(verbs.count(v) for v in ('keep', 'absorb', 'deprecate'))
    merged, retired, new = verbs.count('merge-into'), verbs.count('retire'), verbs.count('new')
    return kept, merged, retired, new


def check_rows(actual_rows, expected):
    assert sorted(actual_rows) == sorted(expected), (
        'rows do not match the decisions: missing %s, unexpected %s' % (
            sorted(set(expected) - set(actual_rows)), sorted(set(actual_rows) - set(expected))))
    subjects = [entity for _, entity, _ in actual_rows]
    assert len(subjects) == len(set(subjects)), 'an entity appears in more than one row'


def terms(text):
    """Content words of a decision fact, cut to a 5-letter stem so light paraphrase still matches."""
    words = re.findall(r"[a-z0-9][a-z0-9'-]*", text.lower())
    return {w[:5] for w in words if w not in STOPWORDS and (len(w) >= 4 or w.isdigit())}


def reflects(written, fact):
    """True when a written line carries enough of the decision's own key terms (about a third, at least one)."""
    wanted = terms(fact)
    return not wanted or len(wanted & terms(written)) >= max(1, -(-len(wanted) // 3))


def check_units(units, decisions):
    """One section per decided unit: its rows, a Why and What's lost grounded in the decision, retire evidence."""
    assert len(units) == len(decisions['units']), 'one section per unit of work'
    for unit in decisions['units']:
        names = {row['entity'] for row in unit['rows']}
        holder = [s for s in units if names == {e for _, e, _ in s['rows']}]
        assert len(holder) == 1, 'unit regrouped or split: ' + unit['intent']
        why, lost = field(holder[0], 'Why'), field(holder[0], "What's lost")
        assert why, 'unit has no Why line: ' + unit['intent']
        assert lost, 'unit has no What\'s lost line: ' + unit['intent']
        assert reflects(why, unit.get('why', '')), 'Why line does not state the decision\'s reason: ' + unit['intent']
        if not unit['lost'].lower().startswith('nothing'):
            assert not NO_LOSS.match(lost.strip(' .')), 'real loss reported as nothing: ' + unit['intent']
        nothing_lost = unit['lost'].lower().strip(' .') in ('nothing', 'none')
        assert (NO_LOSS.match(lost.strip(' .')) if nothing_lost else reflects(lost, unit['lost'])), (
            'What\'s lost line does not state the decision\'s loss: ' + unit['intent'])
        if any(row['verb'] == 'retire' for row in unit['rows']):
            evidence = field(holder[0], 'Evidence')
            assert evidence, 'retire carries no evidence line: ' + unit['intent']
            assert reflects(evidence, unit.get('evidence', '')), 'evidence line does not match the decision: ' + unit['intent']


def check_layout(sections, decisions):
    """The unit sections and the closing Unchanged section every map carries, finished or draft."""
    check_units(section(sections, 'unit'), decisions)
    unchanged = section(sections, 'unchanged')
    assert len(unchanged) == (1 if decisions.get('unchanged') else 0), 'closing Unchanged section only when something is unchanged'


def check_reconciliation(sections, inventory, rows):
    """Both equations, with operands re-derived from the rows, plus the two row checks."""
    reconciliation = section(sections, 'reconciliation')
    assert len(reconciliation) == 1, 'Reconciliation section is required'
    lines = [line.strip() for line in reconciliation[0]['lines'] if line.strip()]
    assert lines and not any('FAIL' in line.upper() for line in lines), 'reconciliation must be present and passing'
    kept, merged, retired, new = derived_counts(rows)
    equations = (
        (RECON_REMOVED, (len(inventory), kept, merged, retired), 'N = K + X + R'),
        (RECON_AFTER, (kept + new, kept, new), 'M = K + W'),
    )
    for pattern, operands, label in equations:
        found = [m for m in map(pattern.match, lines) if m]
        assert len(found) == 1, 'reconciliation needs one passing "%s" line' % label
        assert tuple(int(n) for n in found[0].groups()) == operands, '%s operands do not match the rows' % label
    for label in ('Every inventory entity appears once', 'Every merge-into target survives'):
        assert any(re.match(re.escape(label) + r':\s*OK\s*$', line, re.I) for line in lines), 'reconciliation needs "%s: OK"' % label


def positive():
    inventory = [n for n in (INPUTS / 'inventory.txt').read_text(encoding='utf-8').split() if n]
    decisions = read_json(INPUTS / 'decisions.json')
    text = Path('consolidation-map.md').read_text(encoding='utf-8')
    counts, sections = parse_map(text)
    rows = [row for s in sections for row in s['rows']]
    expected = expected_rows(decisions)
    check_rows(rows, expected)
    after_names = {e for v, e, _ in rows if v in ('keep', 'new', 'absorb', 'deprecate')}
    for verb, entity, target in rows:
        assert verb != 'merge-into' or target in after_names, 'merge-into target does not survive: ' + target
        assert verb == 'new' or entity in inventory, 'row for an entity outside the inventory: ' + entity
    kept, merged, retired, new = derived_counts(rows)
    assert len(inventory) == kept + merged + retired, 'before-inventory does not equal kept + merged-away + retired'
    assert counts == (len(inventory), kept + new, kept + new - len(inventory)), 'counts line does not match the rows'
    check_layout(sections, decisions)
    check_reconciliation(sections, inventory, rows)


def near():
    inventory = [n for n in (INPUTS / 'inventory.txt').read_text(encoding='utf-8').split() if n]
    decisions = read_json(INPUTS / 'decisions.json')
    expected = expected_rows(decisions)
    decided = {entity for _, entity, _ in expected}
    undecided = [n for n in inventory if n not in decided]
    assert len(undecided) == 1, 'task input must leave exactly one entity undecided'
    gap = undecided[0]
    text = Path('consolidation-map.md').read_text(encoding='utf-8')
    counts_line = [m for m in map(COUNTS_DRAFT.match, text.splitlines()) if m]
    assert counts_line, 'the map opens with a "Before N | After M | Net D" counts line (After and Net may be draft values)'
    assert int(counts_line[0].group(1)) == len(inventory), 'counts line Before does not match the inventory'
    _, sections = parse_map(text)
    rows = [row for s in sections for row in s['rows']]
    assert not any(gap in (entity, target) for _, entity, target in rows), 'a disposition was invented for ' + gap
    check_rows(rows, expected)
    check_layout(sections, decisions)
    flagged = [line for line in text.splitlines() if gap in line and 'UNDECIDED' in line]
    assert flagged, gap + ' must be named UNDECIDED'
    reconciliation = section(sections, 'reconciliation')
    assert len(reconciliation) == 1, 'Reconciliation section is required'
    body = '\n'.join(reconciliation[0]['lines'])
    assert 'RECONCILIATION FAILED' in body and gap in body, 'an undecided entity must fail reconciliation, naming it'


def main():
    card = os.environ['AGENTIC_CARD_ID']
    if card == 'consolidation-map-pos-01': positive()
    elif card == 'consolidation-map-near-01': near()
    else: raise AssertionError('unknown consolidation-map task')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
