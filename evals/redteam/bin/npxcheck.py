#!/usr/bin/env python3
"""bin/npxcheck.py <redteam-root> — prints one path per line for every file
under <redteam-root> (excluding .artifacts/) that contains an actual `npx`
INVOCATION shape (design §10.5, counterfeit fixture 26's mutation:
`npx promptfoo@latest`), never on the bare word.

Comment lines (# ... or // ...) are excluded, since this lane's own
diagnostic strings and header prose necessarily NAME the ban ("npx
reference in evals/redteam", a worked example of the mutation) without
being a real invocation. Real invocation code is what must never appear;
prose about it is fine and is how this very file, and run.sh, discuss it.

Exit 0 always; the caller (run.sh) treats non-empty stdout as a failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

INVOCATION_RE = re.compile(r"\bnpx(\s+-[A-Za-z-]+)*\s+promptfoo\b|\bnpx@promptfoo\b")
COMMENT_RE = re.compile(r"^\s*(#|//)")
EXTS = (".sh", ".js", ".yaml", ".yml", ".json")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: npxcheck.py <redteam-root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in EXTS:
            continue
        if ".artifacts" in path.relative_to(root).parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if COMMENT_RE.match(line):
                continue
            if INVOCATION_RE.search(line):
                hits.append(str(path))
                break
    for h in hits:
        print(h)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
