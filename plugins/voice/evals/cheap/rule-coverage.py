#!/usr/bin/env python3
"""Rule-coverage guard for the voice plugin's cheap tier.

The rest of checks.sh asserts that specific load-bearing sentences are present.
This guard asserts the inverse and is what makes "every rule has a test" a
property rather than a habit: it walks each SKILL.md, extracts every normative
RULE UNIT, and fails when a unit has no assertion in THIS file.

Adding a rule to a skill without adding a check for it turns the cheap tier red.
That is the point — a rule nobody tests is a rule that can be silently deleted.

USAGE
    rule-coverage.py <checks.sh> <VAR>=<skill.md> [<VAR>=<skill.md> ...]

The VAR is the shell variable checks.sh uses for that file (_HV, _MV, ...).
Coverage is scoped BY THAT VAR: an assertion against $_HV can only cover a rule
in human-voice. Without the scoping, any pattern anywhere in checks.sh marked
any rule in any skill covered, and a brand-new rule could be born "covered" by
an unrelated check that happened to share a substring with it.

WHAT COUNTS AS A RULE UNIT
A bullet (with its continuation lines) or a paragraph carrying a normative
marker. Wrapped lines are joined first, so an assertion may match text spanning
a line break. The markers:

  - **ALWAYS** / **NEVER**, anywhere in the unit — including inside a
    blockquote, because an invariant is still an invariant when it is quoted
  - a bold lead-in bullet: `- **Thing** — ...`
  - a bolded Never/Always/Do not/Don't
  - a bullet opening with an unbolded normative verb: `- Never ...`

EXCLUDED, deliberately, because they are not rules:
  - fenced code and the output-format templates inside it
  - blockquoted prose WITHOUT an ALWAYS/NEVER marker (a sample response is an
    illustration, not an instruction)
  - bare section labels — a bold run that is the whole line AND ends in ':'
  - headings

THE RESIDUAL, stated plainly: extraction is marker-based. A normative sentence
written as an unmarked mid-paragraph clause carries no marker and is not
extracted, so it is not covered by this guard. The markers above are the ones
the four skills actually use; a rule phrased outside them needs its check
written by hand, the same as before this guard existed.
"""
import re
import sys

MARKER_STRONG = re.compile(r"\*\*(ALWAYS|NEVER)\*\*")
MARKER = re.compile(r"\*\*(ALWAYS|NEVER)\*\*|\*\*(Never|Always|Do not|Don't)\b")
BOLD_LEAD = re.compile(r"^[-*]\s*\*\*[^*]+\*\*")
BARE_NORMATIVE = re.compile(r"^[-*]\s*(Never|Always|Do not|Don't)\b")
LABEL_ONLY = re.compile(r"^\*\*[^*]+\*\*:$")     # trailing colon REQUIRED


def rule_units(path):
    """Yield (line_no_in_file, joined_text) for each normative unit."""
    text = open(path, encoding="utf-8").read()
    offset = 0
    if text.startswith("---\n") and "\n---\n" in text:          # strip frontmatter
        head, text = text.split("\n---\n", 1)
        offset = head.count("\n") + 2      # frontmatter lines + the closing '---'

    units, cur, start, fence = [], [], None, False
    for lineno, raw in enumerate(text.split("\n"), 1):
        s = raw.strip()
        if s.startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        starts_unit = s.startswith(("- ", "* ")) or s.startswith("#")
        if not s or starts_unit:
            if cur:
                units.append((start, " ".join(cur)))
            cur, start = [], None
        if not s or s.startswith("#"):
            continue
        if not cur:
            start = lineno
        cur.append(s)
    if cur:
        units.append((start, " ".join(cur)))

    for lineno, u in units:
        if u.startswith(">") and not MARKER_STRONG.search(u):
            continue                                    # illustration, not a rule
        if LABEL_ONLY.match(u):
            continue
        if MARKER.search(u) or BOLD_LEAD.match(u) or BARE_NORMATIVE.match(u):
            yield lineno + offset, u


def assertions(path):
    """{file_var: [(is_regex, pattern), ...]} for every positive assertion."""
    src = open(path, encoding="utf-8").read()
    out = {}
    # Single- OR double-quoted pattern argument; both forms appear in checks.sh.
    for kind, var, sq, dq in re.findall(
        r"""^(has|hasE)\s+"\$(_\w+)"\s+(?:'([^']+)'|"([^"]+)")""", src, re.M
    ):
        out.setdefault(var, []).append((kind == "hasE", sq or dq))
    return out


def covered(unit, pats):
    for is_re, pat in pats:
        if is_re:
            try:
                if re.search(pat, unit):
                    return True
            except re.error:
                continue
        elif pat in unit:
            return True
    return False


def main():
    checks, targets = sys.argv[1], sys.argv[2:]
    by_var = assertions(checks)
    gaps, total = [], 0
    for spec in targets:
        var, _, path = spec.partition("=")
        if not path:
            print(f"USAGE\texpected VAR=path, got {spec!r}")
            return 2
        pats = by_var.get(var, [])
        for lineno, unit in rule_units(path):
            total += 1
            if not covered(unit, pats):
                gaps.append((path, lineno, unit))
    for path, lineno, unit in gaps:
        print(f"UNENFORCED\t{path}:{lineno}\t{unit[:150]}")
    print(f"TOTAL\t{total}\tUNENFORCED\t{len(gaps)}")
    return 1 if gaps else 0


sys.exit(main())
