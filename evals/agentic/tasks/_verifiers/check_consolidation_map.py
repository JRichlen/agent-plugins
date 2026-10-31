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
EMPTY_LOSS = {'nothing', 'none', 'n/a', 'no loss'}


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


def positive():
    inventory = [n for n in (INPUTS / 'inventory.txt').read_text(encoding='utf-8').split() if n]
    decisions = read_json(INPUTS / 'decisions.json')
    text = Path('consolidation-map.md').read_text(encoding='utf-8')
    counts, sections = parse_map(text)
    units = section(sections, 'unit')
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
    assert len(units) == len(decisions['units']), 'one section per unit of work'
    for unit in decisions['units']:
        names = {row['entity'] for row in unit['rows']}
        holder = [s for s in units if names == {e for _, e, _ in s['rows']}]
        assert len(holder) == 1, 'unit regrouped or split: ' + unit['intent']
        why, lost = field(holder[0], 'Why'), field(holder[0], "What's lost")
        assert why, 'unit has no Why line: ' + unit['intent']
        assert lost, 'unit has no What\'s lost line: ' + unit['intent']
        if not unit['lost'].lower().startswith('nothing'):
            assert lost.lower().strip(' .') not in EMPTY_LOSS, 'real loss reported as nothing: ' + unit['intent']
        if any(row['verb'] == 'retire' for row in unit['rows']):
            assert 'evidence' in '\n'.join(holder[0]['lines']).lower(), 'retire carries no evidence line'
    unchanged = section(sections, 'unchanged')
    assert len(unchanged) == (1 if decisions.get('unchanged') else 0), 'closing Unchanged section only when something is unchanged'
    reconciliation = section(sections, 'reconciliation')
    assert len(reconciliation) == 1, 'Reconciliation section is required'
    body = '\n'.join(reconciliation[0]['lines'])
    assert body.strip() and 'FAIL' not in body.upper(), 'reconciliation must be present and passing'


def near():
    inventory = [n for n in (INPUTS / 'inventory.txt').read_text(encoding='utf-8').split() if n]
    decisions = read_json(INPUTS / 'decisions.json')
    expected = expected_rows(decisions)
    decided = {entity for _, entity, _ in expected}
    undecided = [n for n in inventory if n not in decided]
    assert len(undecided) == 1, 'task input must leave exactly one entity undecided'
    gap = undecided[0]
    text = Path('consolidation-map.md').read_text(encoding='utf-8')
    _, sections = parse_map(text)
    rows = [row for s in sections for row in s['rows']]
    assert not any(gap in (entity, target) for _, entity, target in rows), 'a disposition was invented for ' + gap
    check_rows(rows, expected)
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
