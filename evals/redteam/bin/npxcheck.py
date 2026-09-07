#!/usr/bin/env python3
"""bin/npxcheck.py <redteam-root> — prints one path per line for every file
under <redteam-root> (excluding .artifacts/) that contains an actual
NETWORK-RESOLVING PACKAGE-RUNNER invocation of promptfoo (design §10.5,
counterfeit fixture 26's mutation), never the bare word.

Comment lines (# ... or // ...) are excluded, since this lane's own
diagnostic strings and header prose necessarily NAME the ban ("npx
reference in evals/redteam", a worked example of the mutation) without
being a real invocation. Real invocation code is what must never appear;
prose about it is fine and is how this very file, and run.sh, discuss it.

Widened 2026-09-06 after a measured evasion. The previous version scanned
only ('.sh', '.js', '.yaml', '.yml', '.json') -- and every script in bin/
except two is PYTHON, so `.py` was the single largest blind spot in this
tree. It also knew only ONE resolver. Three real invocations appended to
three real files in a scratch copy:
#
#   bin/freeze.py     subprocess.run(["npx", "promptfoo@latest", "eval"])
#   bin/promptfoo.sh  npm exec -- promptfoo@latest --version
#   bin/netproof.sh   bunx promptfoo@latest --version
#
produced ZERO hits, and run.sh went on to print "OK -- 0 npx references".
The extension set now covers the interpreted/config file types this tree
actually uses plus extensionless executables, and the pattern covers every
package runner that resolves over the network, not just one of them.

Those three example lines are `#`-prefixed INSIDE this docstring on purpose:
`.py` is now scanned, so the comment-stripping below is the only thing that
keeps this file's own worked example from reporting itself. Any prose that
names a resolver and the package on ONE line, anywhere in a scanned file,
must be written as a comment line for the same reason.

Exit 0 always; the caller (run.sh) treats non-empty stdout as a failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Split across three statements ON PURPOSE: `.py` is now a scanned
# extension, so no single line of any scanned file may contain both a
# resolver token and the package name, or this checker would report itself.
_RESOLVERS = r"npx|bunx|pnpm\s+dlx|yarn\s+dlx|npm\s+exec|deno\s+run"
_PACKAGE = r"promptfoo"
INVOCATION_RE = re.compile(rf"\b(?:{_RESOLVERS})\b[^\n]*?\b{_PACKAGE}\b")

COMMENT_RE = re.compile(r"^\s*(#|//)")
EXTS = (
    ".sh", ".bash", ".js", ".mjs", ".cjs", ".ts", ".mts", ".cts",
    ".py", ".yaml", ".yml", ".json", ".toml", ".mk",
)
# Files a build or CI step executes that carry no extension at all.
EXTENSIONLESS_NAMES = ("Makefile", "GNUmakefile", "Dockerfile", "entrypoint", "run")


def _is_scanned(path: Path) -> bool:
    if path.suffix in EXTS:
        return True
    if path.suffix == "" and path.name in EXTENSIONLESS_NAMES:
        return True
    # Any other extensionless file that is executable: a shell script with no
    # `.sh` is exactly how the previous extension allowlist would be walked
    # around a second time.
    return path.suffix == "" and path.stat().st_mode & 0o111 != 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: npxcheck.py <redteam-root>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1])
    hits: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if ".artifacts" in path.relative_to(root).parts:
            continue
        try:
            if not _is_scanned(path):
                continue
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
