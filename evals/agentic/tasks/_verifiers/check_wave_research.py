#!/usr/bin/env python3
"""Recompute each sub-claim's verdict from the supplied evidence and compare.

The deliverable's own labels are never trusted: the expected verdict for every
claim is derived from ``evidence.json`` by the skill's supported rule, and the
table in ``thesis.md`` must agree with it. A claim backed by one incentive
class, or by no primary source, may not be written as supported.
"""
import json
import os
from pathlib import Path
import re
import sys

INPUTS = Path(os.environ.get('AGENTIC_INPUTS', '/inputs'))
VERDICTS = ('supported', 'unverified', 'mixed', 'refuted', 'unknown')
HEADER = re.compile(r'^THESIS v0 (?:->|→) v2:\s*(\S.*)$')
LABEL = re.compile(r'^[A-Z][A-Z /]+:')
CLAIM_ID = re.compile(r'^C\d+$')
MIN_MIND_WORDS = 4


def expected_verdict(evidence):
    """The skill's rule: supported needs no refuter, two incentive classes and one primary source."""
    support = [e for e in evidence if e['direction'] == 'supports']
    refute = [e for e in evidence if e['direction'] == 'refutes']
    if not evidence:
        return 'unknown'
    if support and refute:
        return 'mixed'
    if refute:
        return 'refuted'
    classes = {e['incentive'] for e in support}
    if len(classes) >= 2 and any(e['primary'] for e in support):
        return 'supported'
    return 'unverified'


def parse_table(text):
    """Rows of the claims table as {id: (verdict, probability text, mind text)}."""
    rows = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) != 4 or not CLAIM_ID.match(cells[0]):
            continue
        assert cells[0] not in rows, 'claim %s appears in two rows' % cells[0]
        rows[cells[0]] = (cells[1].lower(), cells[2], cells[3])
    return rows


def labelled(text, label):
    """The text of one ``LABEL:`` paragraph, up to the next label or blank line."""
    out, on = [], False
    for line in text.splitlines():
        if line.startswith(label):
            on = True
            out.append(line[len(label):])
            continue
        if on and (not line.strip() or LABEL.match(line)):
            break
        if on:
            out.append(line)
    return ' '.join(out).strip()


def probability(cell):
    cell = cell.strip()
    value = float(cell[:-1]) / 100 if cell.endswith('%') else float(cell)
    assert 0 <= value <= 1, 'probability outside 0..1: ' + cell
    return value


def check(near):
    evidence = json.loads((INPUTS / 'evidence.json').read_text(encoding='utf-8'))
    text = Path('thesis.md').read_text(encoding='utf-8')
    lines = text.splitlines()
    assert lines and HEADER.match(lines[0]), 'line 1 must read "THESIS v0 -> v2: <what changed or why nothing moved>"'
    rows = parse_table(text)
    expected = {c['id']: expected_verdict(c['evidence']) for c in evidence['claims']}
    assert set(rows) == set(expected), 'table rows %s do not match the claims %s' % (sorted(rows), sorted(expected))
    for cid, want in expected.items():
        verdict, prob, mind = rows[cid]
        assert verdict in VERDICTS, '%s verdict is not one of the five labels: %s' % (cid, verdict)
        assert verdict == want, '%s is %s on this evidence, not %s' % (cid, want, verdict)
        value = probability(prob)
        assert verdict != 'supported' or value > 0.5, cid + ' is supported but its probability is not above 0.5'
        assert verdict != 'refuted' or value < 0.5, cid + ' is refuted but its probability is not below 0.5'
        assert len(mind.split()) >= MIN_MIND_WORDS, cid + ' has no concrete "would change my mind"'
    guards = labelled(text, 'GUARDS:')
    dead_ends = labelled(text, 'UNKNOWNS / DEAD ENDS:')
    assert guards, 'a GUARDS: line is required'
    assert dead_ends, 'an UNKNOWNS / DEAD ENDS: line is required'
    for cid, want in expected.items():
        if want in ('unverified', 'mixed'):
            assert re.search(r'\b%s\b' % cid, guards), '%s is %s and must be named in GUARDS' % (cid, want)
        if want == 'unknown':
            assert re.search(r'\b%s\b' % cid, dead_ends), '%s has no evidence and must be named in UNKNOWNS / DEAD ENDS' % cid
    if near:
        assert not any(w == 'supported' for w in expected.values()), 'near-miss input must leave no claim supported'
        assert re.search(r'single|one (?:community|source|class)|vendor[- ]only', guards, re.I), 'GUARDS must flag the claims as resting on one community'


def main():
    card = os.environ['AGENTIC_CARD_ID']
    if card == 'wave-research-pos-01': check(near=False)
    elif card == 'wave-research-near-01': check(near=True)
    else: raise AssertionError('unknown wave-research task')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
