#!/usr/bin/env python3
"""Check the files a delegated-intelligence run leaves on disk.

Nothing here reads a prose claim. The expected finding for each service is
derived from the supplied ``services/*.conf`` by a fixed rule, and the checks
compare what is on disk against it. A finding is a key AND its value, both read
from the config, so an output or report row that names the right setting with the
wrong value fails:

* pos: an interrupted fan-out. Every handback says "done", but one output is
  empty and one was never written. The run must regenerate exactly those two
  from the configs (each with its own non-empty ``briefs/<service>.md``), leave the two complete outputs byte-identical, make
  ``report.md`` true to the configs (setting, value and source file per row), and leave ``status.md`` matching the disk
  (state, attempts, and an output file behind every row).
* near: one known file, an answer needed now. The answer must be right and no
  delegation artifacts (board, briefs, outputs, handbacks) may exist.
"""
import os
from pathlib import Path
import re
import sys

INPUTS = Path(os.environ.get('AGENTIC_INPUTS', '/inputs'))
TIERS = ('haiku', 'sonnet', 'opus')
DONE = ('landed', 'verified')
MAX_ATTEMPTS = 3
FANOUT_ARTIFACTS = ('briefs', 'status.md', 'out', 'handbacks')

RISKY = {
    'admin_password': lambda v: v == 'admin',
    'tls_verify': lambda v: v.lower() == 'false',
    'cors_origin': lambda v: v == '*',
    'request_timeout': lambda v: v == '0',
}


def settings(path):
    """The ``key = value`` pairs of one config, comments and blanks dropped."""
    out = {}
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = (part.strip() for part in line.split('=', 1))
        out[key] = value
    return out


def risky_pairs(root):
    """{service: (risky key, its configured value)}; exactly one risky setting per service."""
    found = {}
    for conf in sorted((root / 'services').glob('*.conf')):
        hits = [(k, v) for k, v in settings(conf).items() if k in RISKY and RISKY[k](v)]
        assert len(hits) == 1, '%s must hold exactly one risky setting, found %s' % (conf.name, [k for k, _ in hits])
        found[conf.stem] = hits[0]
    assert found, 'no services supplied'
    return found


def mentions(text, key):
    return bool(re.search(r'(?<![\w])%s(?![\w])' % re.escape(key), text, re.I))


# Wrapping a key or value in backticks or quotes, and any spacing around ``=`` or
# ``:``, are formatting, not content. The value must end where it ends: ``0`` is
# not ``05`` or ``0.5``, but a sentence-final ``0.`` is still ``0``.
WRAP = '[`"\']*'


def states(text, key, value):
    """True when ``text`` says ``key = value`` (``=`` or ``:``), whatever the spacing, quoting or case."""
    pattern = r'(?<![\w])%s%s\s*[=:]\s*%s%s%s(?![\w])(?!\.\d)' % (
        re.escape(key), WRAP, WRAP, re.escape(value), WRAP)
    return bool(re.search(pattern, text, re.I))


def names_only(text, own, everything):
    """True when ``text`` states its own risky key and value and names no other service's key."""
    key, value = own
    return states(text, key, value) and not any(mentions(text, k) for k, _ in everything if k != key)


def table(path, cells):
    """Rows of the first markdown table with ``cells`` columns, header dropped."""
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line.startswith('|'):
            continue
        row = [c.strip() for c in line.strip('|').split('|')]
        if len(row) != cells or set(''.join(row)) <= set('-: '):
            continue
        rows.append(row)
    return rows[1:] if rows else rows


def complete(path, own):
    """A seeded output that already holds its service's finding, key and value."""
    return path.is_file() and bool(path.read_text(encoding='utf-8').strip()) and states(path.read_text(encoding='utf-8'), *own)


def check_pos():
    keys = risky_pairs(INPUTS)
    ws = Path('.')
    for name in keys:
        assert (ws / 'services' / (name + '.conf')).read_bytes() == (INPUTS / 'services' / (name + '.conf')).read_bytes(), \
            'services/%s.conf was edited; shared inputs are read-only' % name
    seeded_board = {r[2]: r for r in table(INPUTS / 'status.md', 5)}
    kept, lost = [], []
    for name, key in keys.items():
        (kept if complete(INPUTS / 'out' / (name + '.md'), key) else lost).append(name)
    assert kept and lost, 'the seeded state must hold complete and lost outputs'
    for name in kept:
        rel = 'out/%s.md' % name
        assert (ws / rel).is_file() and (ws / rel).read_bytes() == (INPUTS / rel).read_bytes(), \
            '%s was complete and must be left exactly as it was' % rel
    for name in lost:
        path = ws / 'out' / (name + '.md')
        assert path.is_file() and path.read_text(encoding='utf-8').strip(), 'out/%s.md is missing or empty behind a "done" handback' % name
        brief = ws / 'briefs' / (name + '.md')
        assert brief.is_file() and brief.read_text(encoding='utf-8').strip(), \
            'briefs/%s.md is missing or empty: every task you run or re-run gets its own brief' % name
        assert names_only(path.read_text(encoding='utf-8'), keys[name], keys.values()), \
            'out/%s.md must state %s = %s, the risky setting in %s.conf, and name no other service\'s' % (name, keys[name][0], keys[name][1], name)
    report = ws / 'report.md'
    assert report.is_file(), 'report.md is required'
    rows = {r[0].lower(): r for r in table(report, 3)}
    assert set(rows) == set(keys), 'report rows %s do not match the services %s' % (sorted(rows), sorted(keys))
    for name, key in keys.items():
        assert names_only(rows[name][1], key, keys.values()), 'the report row for %s must state %s = %s and name no other service\'s setting' % (name, key[0], key[1])
        source = re.sub(r'^\./', '', rows[name][2].strip('`"\' '))
        assert source == 'out/%s.md' % name and (ws / source).is_file(), \
            'the report row for %s must cite its own output, out/%s.md, and that file must exist (it cites %r)' % (name, name, rows[name][2])
    board = table(ws / 'status.md', 5) if (ws / 'status.md').is_file() else []
    assert board, 'status.md must keep its board table'
    by_path = {}
    for row in board:
        assert row[2] not in by_path, 'two board rows claim %s' % row[2]
        by_path[row[2]] = row
    assert set(by_path) == {'out/%s.md' % n for n in keys}, 'board rows %s do not match the tasks' % sorted(by_path)
    for name in keys:
        rel = 'out/%s.md' % name
        _task, _tier, _path, state, attempts = by_path[rel]
        assert state in DONE, '%s is %s on the board; a finished task is landed or verified' % (rel, state)
        assert attempts.isdigit(), '%s has a non-numeric attempt count' % rel
        before = int(seeded_board[rel][4])
        if name in kept:
            assert int(attempts) == before, '%s was never re-run and must keep its attempt count of %d' % (rel, before)
        else:
            assert before + 1 <= int(attempts) <= MAX_ATTEMPTS, '%s was re-run and must show between %d and %d attempts' % (rel, before + 1, MAX_ATTEMPTS)


def check_near():
    ws = Path('.')
    conf = INPUTS / 'services' / 'billing.conf'
    want = settings(conf)['request_timeout']
    for name in ('api', 'billing', 'search', 'notify'):
        assert (ws / 'services' / (name + '.conf')).read_bytes() == (INPUTS / 'services' / (name + '.conf')).read_bytes(), \
            'services/%s.conf was edited' % name
    answer = ws / 'answer.txt'
    assert answer.is_file(), 'answer.txt is required'
    assert re.fullmatch(r'%s\s*(s|sec|secs|seconds)?' % re.escape(want), answer.read_text(encoding='utf-8').strip(), re.I), \
        'answer.txt must hold billing.conf\'s request_timeout, %s' % want
    for name in FANOUT_ARTIFACTS:
        assert not (ws / name).exists(), '%s exists: a one-file answer needed now is done inline, not fanned out' % name


def main():
    card = os.environ['AGENTIC_CARD_ID']
    if card == 'delegated-intelligence-pos-01': check_pos()
    elif card == 'delegated-intelligence-near-01': check_near()
    else: raise AssertionError('unknown delegated-intelligence task')


if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
