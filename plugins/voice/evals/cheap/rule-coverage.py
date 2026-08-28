#!/usr/bin/env python3
"""Rule-coverage guard for the voice plugin's cheap tier.

The rest of checks.sh asserts that specific load-bearing sentences are present.
This guard asserts the inverse and is what makes "every rule has a test" a
property rather than a habit: it walks each SKILL.md, extracts every normative
RULE UNIT, and fails when a unit has no assertion anywhere in checks.sh.

Adding a rule to a skill without adding a check for it turns this red. That is
the point — a rule nobody tests is a rule that can be silently deleted.

A rule unit is a bullet (with its continuation lines) or a paragraph that
carries a normative marker: **ALWAYS** / **NEVER**, a bold lead-in
(`- **Thing** — ...`), or a bolded Never/Always/Don't. Wrapped lines are joined
first, so an assertion may match text that spans a line break.

Excluded, deliberately, because they are not rules:
  - fenced code and the output-format templates inside it
  - blockquoted EXAMPLES (a sample response is not an instruction)
  - bare section labels — a bold run that is the whole line, ending in ':'
  - headings

Registered assertions are read out of checks.sh itself, so there is one source
of truth and no manifest to drift. Fixed-string (has) patterns must appear
verbatim in the unit; regex (hasE) patterns are matched as regexes.
"""
import re
import sys

CHECKS = sys.argv[1]
SKILLS = sys.argv[2:]

MARKER = re.compile(r"\*\*(ALWAYS|NEVER)\*\*|\*\*(Never|Always|Do not|Don't)\b")
BOLD_LEAD = re.compile(r"^[-*]\s*\*\*[^*]+\*\*")
LABEL_ONLY = re.compile(r"^\*\*[^*]+\*\*:?$")


def rule_units(path):
    """Yield (line_no, joined_text) for each normative unit in a markdown file."""
    text = open(path, encoding="utf-8").read()
    if text.startswith("---\n") and "\n---\n" in text:      # strip frontmatter
        text = text.split("\n---\n", 1)[1]
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
        if u.startswith(">"):                 # example / quoted illustration
            continue
        if LABEL_ONLY.match(u):               # bare section label
            continue
        if MARKER.search(u) or BOLD_LEAD.match(u):
            yield lineno, u


def assertions(path):
    """(is_regex, pattern, file_var) for every positive assertion in checks.sh."""
    out = []
    for kind, var, pat in re.findall(
        r'^(has|hasE)\s+"\$(_\w+)"\s+\'([^\']+)\'', open(path, encoding="utf-8").read(), re.M
    ):
        out.append((kind == "hasE", pat, var))
    return out


def covered(unit, pats):
    for is_re, pat, _ in pats:
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
    pats = assertions(CHECKS)
    gaps, total = [], 0
    for skill in SKILLS:
        for lineno, unit in rule_units(skill):
            total += 1
            if not covered(unit, pats):
                gaps.append((skill, lineno, unit))
    for skill, lineno, unit in gaps:
        print(f"UNENFORCED\t{skill}:{lineno}\t{unit[:150]}")
    print(f"TOTAL\t{total}\tUNENFORCED\t{len(gaps)}")
    return 1 if gaps else 0


sys.exit(main())
