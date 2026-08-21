#!/usr/bin/env python3
"""check-handoff-portability.py — deterministic check for the HANDOFF branch's
pointer-only rule (see skills/context-handoff/references/portable-extraction.md).

A handoff-shaped Markdown file must not contain a block of more than ~3-4
lines of prose lifted from a single external artifact under a heading like
"Spec:", "Plan:", "ADR:", "Issue:", "Commit:", or "Diff:" — such a block must
instead be a short pointer with a path or URL. This script scans a file for
that exact pattern and fails closed: a heading with a long, unquoted-source
block is a violation whether or not the author meant it to be a "real" quote.

Usage:
    check-handoff-portability.py <file.md> [<file2.md> ...]

Exit 0 if every file is clean (every Spec:/Plan:/ADR:/Issue:/Commit:/Diff:
block is either short or carries an adjacent path/URL). Exit 1 if any file
has a violation, with the offending heading and line number printed to
stderr. Exit 2 on usage error.
"""
import re
import sys

HEADING_LABELS = ("Spec", "Plan", "ADR", "Issue", "Commit", "Diff")

# Matches an optional bullet marker, optional markdown heading hashes, optional
# bold markers, then one of the six labels followed by a colon. Captures the
# label and whatever trailing text sits on the same line.
HEADING_RE = re.compile(
    r'^\s*(?:[-*]\s*)?(?:#{1,6}\s*)?\*{0,2}(' + "|".join(HEADING_LABELS) + r')\s*:\*{0,2}\s*(.*)$'
)

# A path-like token (has at least one "/" between word-ish segments) or a URL.
PATH_RE = re.compile(r'https?://\S+|(?<![\w.\-])[\w.\-]+(?:/[\w.\-]+)+')

MAX_UNPOINTED_LINES = 4


def find_violations(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    violations = []
    i = 0
    n = len(lines)
    while i < n:
        m = HEADING_RE.match(lines[i])
        if not m:
            i += 1
            continue
        label = m.group(1)
        block = [lines[i]]
        j = i + 1
        while j < n and lines[j].strip() != "" and not HEADING_RE.match(lines[j]):
            block.append(lines[j])
            j += 1
        block_text = "\n".join(block)
        nonblank = [ln for ln in block if ln.strip()]
        if len(nonblank) > MAX_UNPOINTED_LINES and not PATH_RE.search(block_text):
            violations.append((i + 1, label, len(nonblank)))
        i = j
    return violations


def main(argv):
    if not argv:
        print("usage: check-handoff-portability.py <file.md> [<file2.md> ...]", file=sys.stderr)
        return 2

    had_violation = False
    for path in argv:
        try:
            violations = find_violations(path)
        except OSError as e:
            print(f"{path}: cannot read ({e})", file=sys.stderr)
            return 2
        if violations:
            had_violation = True
            for line, label, count in violations:
                print(
                    f'{path}:{line}: "{label}:" block has {count} lines of quoted '
                    f'prose with no adjacent path/URL — replace with a path/URL '
                    f'pointer to the live source',
                    file=sys.stderr,
                )
        else:
            print(f"{path}: OK — no long quoted blocks without an adjacent path/URL")

    return 1 if had_violation else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
