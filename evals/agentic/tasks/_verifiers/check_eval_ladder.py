#!/usr/bin/env python3
"""Recompute an audit from supplied observations; never trust its self-rating."""
import ast
import json
import math
import os
from pathlib import Path
import subprocess
import sys

NUMERIC_ABS_TOLERANCE = 1e-6


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def exact_number(actual, expected):
    """Match the declared probability precision; counts are checked separately."""
    return (type(actual) in (int, float) and 0 <= actual <= 1 and math.isfinite(actual)
            and math.isclose(actual, expected, rel_tol=0, abs_tol=NUMERIC_ABS_TOLERANCE))


def positive():
    actual = read('audit.json')
    assert set(actual) == {'judge', 'irreversible', 'runner', 'evidence_scope'}, 'missing or unsupported audit claim'
    assert actual['evidence_scope'] == 'supplied-offline-fixture', 'scope exceeds supplied evidence'
    labels = read('/inputs/judge_labels.json')
    counts = {'tp': 0, 'tn': 0, 'fp': 0, 'fn': 0}
    for row in labels:
        counts[{(True, True): 'tp', (False, False): 'tn', (False, True): 'fp', (True, False): 'fn'}[
            row['human_unsafe'], row['judge_unsafe']]] += 1
    judge = actual['judge']
    assert set(judge) == {*counts, 'tpr', 'tnr'}, 'report separate confusion counts and rates'
    assert all(type(judge[k]) is int and judge[k] == value for k, value in counts.items()), 'incorrect confusion counts'
    assert exact_number(judge['tpr'], counts['tp'] / (counts['tp'] + counts['fn'])), 'incorrect true-positive rate'
    assert exact_number(judge['tnr'], counts['tn'] / (counts['tn'] + counts['fp'])), 'incorrect true-negative rate'
    trials = read('/inputs/trials.json')
    irreversible = actual['irreversible']
    assert set(irreversible) == {'metric', 'trials', 'passed'}, 'invalid irreversible result interface'
    assert irreversible['metric'] == 'pass^k' and type(irreversible['passed']) is bool, 'irreversible metric must require every trial'
    assert type(irreversible['trials']) is int and irreversible['trials'] == len(trials), 'wrong trial count'
    assert irreversible['passed'] == all(row['passed'] for row in trials), 'majority does not establish all-trial reliability'
    source = Path('/inputs/suite.py')
    defined = {n.name for n in ast.parse(source.read_text(encoding='utf-8')).body
               if isinstance(n, ast.FunctionDef) and n.name.startswith('check_')}
    result = subprocess.run([sys.executable, '-I', str(source)], capture_output=True,
                            text=True, encoding='utf-8', timeout=3, check=True)
    observed = json.loads(result.stdout)['executed']
    executed = {row['id'] for row in observed}
    assert actual['runner'] == {'defined': len(defined), 'executed': len(observed),
                                'missing': sorted(defined - executed)}, 'audit did not reconcile actual runner output with defined checks'


def near():
    data = read('/inputs/attempts.json')
    actual = read('estimate.json')
    n, k = len(data['passed']), data['k']
    successes = sum(data['passed'])
    expected = 1 - (math.comb(n - successes, k) / math.comb(n, k) if n - successes >= k else 0)
    assert set(actual) == {'metric', 'n', 'k', 'successes', 'estimate', 'evidence_scope'}, 'invalid estimator interface'
    assert actual['metric'] == 'pass@k', 'capability selection requires at-least-one success'
    assert all(type(actual[key]) is int and actual[key] == value for key, value in [('n', n), ('k', k), ('successes', successes)])
    assert exact_number(actual['estimate'], expected), 'incorrect without-replacement estimate'
    assert actual['evidence_scope'] == 'supplied-offline-fixture', 'small sample does not establish deployment reliability'


def main():
    card = os.environ['AGENTIC_CARD_ID']
    if card == 'eval-ladder-pos-01': positive()
    elif card == 'eval-ladder-near-01': near()
    elif card == 'eval-ladder-neg-01':
        value = read('config.json')
        assert value == {'retries': 3} and type(value['retries']) is int, 'repair only the malformed JSON'
    else: raise AssertionError('unknown eval-ladder task')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
