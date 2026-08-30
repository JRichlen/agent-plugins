#!/usr/bin/env python3
"""Behavior-surface trigger guard (RQ-001).

The paid behavioral/routing evals only run when CI's changed-path filters say a
PR touched something behavior-bearing. Those filters used to watch only each
plugin's promptfoo pack and `plugins/*/skills/*/SKILL.md` — so an edit to a
command, a skill reference doc, a plugin AGENTS.md, a hook, or routing-relevant
manifest metadata could steer the model differently and still merge green
without any behavioral evaluation ("green because it did not run").

This guard freezes the behavior-bearing path definition in
`ci/behavior-surfaces.json` and asserts, offline and deterministically:

  1. SYNC — the spec and the paths-filter blocks in
     `.github/workflows/evals.yml` are in verbatim lockstep, both directions
     (`${plugin}` in the spec corresponds to `${{ matrix.plugin }}` in the
     workflow). Widening or narrowing a trigger is a deliberate two-file edit.
  2. COUNTERFEIT TABLE — a fixed table of changed-file cases, evaluated against
     the patterns EXTRACTED FROM THE WORKFLOW ITSELF (not the spec), proves
     that behavior-bearing edits OUTSIDE SKILL.md select the right pack, and
     that unrelated edits select nothing (no spurious paid spend). No model
     call, no network, no repo files needed — pure pattern arithmetic, so it
     runs identically in the counterfeit tier's synthetic root.
  3. AUDIT REPORT — the workflow still announces both outcomes (EVALUATED and
     SKIPPED) for the behavioral and routing legs, so a green check can never
     be mistaken for an exercised one.

Usage:
  check_behavior_surfaces.py --repo <root>   # verify that repo's spec + workflow
  check_behavior_surfaces.py --self-test     # internal fixtures; non-zero on failure
"""
import json
import os
import re
import sys

SPEC_REL = os.path.join("ci", "behavior-surfaces.json")
WORKFLOW_REL = os.path.join(".github", "workflows", "evals.yml")
PLACEHOLDER = "${plugin}"
MATRIX_TOKEN = "${{ matrix.plugin }}"


def load_spec(repo_root):
    with open(os.path.join(repo_root, SPEC_REL)) as fh:
        spec = json.load(fh)
    plugin_paths = spec.get("plugin_behavior_paths")
    routing_paths = spec.get("routing_paths")
    if not isinstance(plugin_paths, list) or not plugin_paths:
        raise ValueError("behavior-surfaces.json: 'plugin_behavior_paths' must be a non-empty list")
    if not isinstance(routing_paths, list) or not routing_paths:
        raise ValueError("behavior-surfaces.json: 'routing_paths' must be a non-empty list")
    return plugin_paths, routing_paths


def glob_to_regex(pattern):
    """Compile a dorny/paths-filter (minimatch-style) glob to a full-match regex.

    Supported forms are the ones this repo's filters actually use:
    `**` crosses directory separators (`a/**/b` also matches `a/b`, `a/**`
    matches anything under `a/`), `*` matches within one path segment.
    """
    esc = re.escape(pattern)
    esc = esc.replace("/\\*\\*/", "/(?:.+/)?")
    if esc.startswith("\\*\\*/"):
        esc = "(?:.+/)?" + esc[len("\\*\\*/"):]
    if esc.endswith("/\\*\\*"):
        esc = esc[: -len("/\\*\\*")] + "/.+"
    esc = esc.replace("\\*\\*", ".*")
    esc = esc.replace("\\*", "[^/]*")
    return re.compile("^" + esc + "$")


def selects(patterns, changed_file):
    return any(glob_to_regex(p).match(changed_file) for p in patterns)


def extract_filter_globs(workflow_text, key):
    """Extract the quoted glob list under `<key>:` in a `filters: |` block."""
    lines = workflow_text.splitlines()
    out = []
    for idx, line in enumerate(lines):
        if line.strip() != f"{key}:":
            continue
        key_indent = len(line) - len(line.lstrip())
        for l2 in lines[idx + 1:]:
            if not l2.strip():
                break
            ind = len(l2) - len(l2.lstrip())
            s = l2.strip()
            if ind <= key_indent or not s.startswith("- "):
                break
            out.append(s[2:].strip().strip("'\""))
    return out


# ── Counterfeit table ────────────────────────────────────────────────────────
# Each case is pure pattern arithmetic against the WORKFLOW's own filter globs
# (with the matrix token substituted), so it needs no repo files and no model.
# The first case is THE RQ-001 counterfeit: a behavior-bearing edit outside
# SKILL.md that the pre-fix filters left green-without-evaluation.
BEHAVIORAL_CASES = [
    # (plugin whose leg is billed, changed file, expected selected?, why)
    ("graveyard", "plugins/graveyard/commands/bury.md", True,
     "command markdown steers the model — behavior edit OUTSIDE SKILL.md (RQ-001 counterfeit)"),
    ("redgate", "plugins/redgate/skills/redgate/references/verified-rounds.md", True,
     "skill reference docs are progressively disclosed into context"),
    ("redgate", "plugins/redgate/hooks/session-gate.sh", True,
     "hooks change runtime behavior"),
    ("graveyard", "plugins/graveyard/AGENTS.md", True,
     "plugin AGENTS.md is the harness's entry map into the plugin"),
    ("graveyard", "plugins/graveyard/.claude-plugin/plugin.json", True,
     "manifest description is routing-relevant metadata"),
    ("graveyard", "plugins/graveyard/skills/graveyard/SKILL.md", True,
     "SKILL.md prose (the original trigger surface)"),
    ("graveyard", "plugins/graveyard/evals/promptfoo/promptfooconfig.yaml", True,
     "the pack itself changed"),
    ("graveyard", "evals/paid/pass-rate.sh", True,
     "the shared paid harness changed"),
    ("graveyard", "plugins/graveyard/docs/upkeep.md", False,
     "plugin docs/ prose is not a behavior surface — must not bill a paid leg"),
    ("graveyard", "README.md", False,
     "repo-level docs are not a behavior surface"),
    ("redgate", "plugins/graveyard/commands/bury.md", False,
     "another plugin's surface must not bill this plugin's leg"),
    ("graveyard", "plugins/graveyard/skills/graveyard/scripts/archive-repo.sh", False,
     "guard scripts are the DEEP tier's frozen surface, not the behavioral pack's"),
]

ROUTING_CASES = [
    # (changed file, expected selected?, why)
    ("evals/routing/prompt.txt", True, "the routing pack itself"),
    ("plugins/graveyard/skills/graveyard/SKILL.md", True,
     "skill descriptions feed the roster"),
    (".claude-plugin/marketplace.json", True,
     "marketplace descriptions are what gen-roster.sh renders"),
    ("plugins/graveyard/.claude-plugin/plugin.json", True,
     "manifest descriptions are parity-locked to the marketplace entry"),
    ("README.md", False, "repo docs do not feed the roster"),
    ("plugins/graveyard/commands/bury.md", False,
     "commands are the plugin pack's surface, not the roster's"),
]


def run_counterfeit_table(paid_globs_template, routing_globs):
    """Evaluate both tables; return (ok, messages)."""
    msgs = []
    ok = True
    for plugin, changed, expected, why in BEHAVIORAL_CASES:
        patterns = [g.replace(MATRIX_TOKEN, plugin) for g in paid_globs_template]
        got = selects(patterns, changed)
        verdict = "selected" if got else "not selected"
        if got == expected:
            msgs.append(f"PASS behavioral[{plugin}] {changed} -> {verdict} ({why})")
        else:
            ok = False
            msgs.append(f"FAIL behavioral[{plugin}] {changed} -> {verdict}, expected "
                        f"{'selected' if expected else 'not selected'} ({why})")
    for changed, expected, why in ROUTING_CASES:
        got = selects(routing_globs, changed)
        verdict = "selected" if got else "not selected"
        if got == expected:
            msgs.append(f"PASS routing {changed} -> {verdict} ({why})")
        else:
            ok = False
            msgs.append(f"FAIL routing {changed} -> {verdict}, expected "
                        f"{'selected' if expected else 'not selected'} ({why})")
    return ok, msgs


def check_repo(repo_root):
    msgs = []
    plugin_paths, routing_paths = load_spec(repo_root)
    wf_path = os.path.join(repo_root, WORKFLOW_REL)
    if not os.path.exists(wf_path):
        msgs.append(f"no {WORKFLOW_REL} present — behavior-surface check inert here")
        return True, msgs
    with open(wf_path) as fh:
        text = fh.read()
    ok = True

    # 1. SYNC — spec <-> workflow, both directions, verbatim.
    wf_paid = extract_filter_globs(text, "paid")
    wf_routing = extract_filter_globs(text, "routing")
    spec_paid_as_wf = [p.replace(PLACEHOLDER, MATRIX_TOKEN) for p in plugin_paths]
    if set(wf_paid) == set(spec_paid_as_wf) and wf_paid:
        msgs.append(f"PASS behavioral 'paid' filter in lockstep with the spec ({len(wf_paid)} patterns)")
    else:
        ok = False
        missing = sorted(set(spec_paid_as_wf) - set(wf_paid))
        extra = sorted(set(wf_paid) - set(spec_paid_as_wf))
        for m in missing:
            msgs.append(f"FAIL behavioral filter is missing spec pattern: {m}")
        for e in extra:
            msgs.append(f"FAIL behavioral filter carries a pattern the spec does not: {e}")
        if not wf_paid:
            msgs.append("FAIL could not extract any 'paid' filter globs from the workflow")
    if set(wf_routing) == set(routing_paths) and wf_routing:
        msgs.append(f"PASS routing filter in lockstep with the spec ({len(wf_routing)} patterns)")
    else:
        ok = False
        missing = sorted(set(routing_paths) - set(wf_routing))
        extra = sorted(set(wf_routing) - set(routing_paths))
        for m in missing:
            msgs.append(f"FAIL routing filter is missing spec pattern: {m}")
        for e in extra:
            msgs.append(f"FAIL routing filter carries a pattern the spec does not: {e}")
        if not wf_routing:
            msgs.append("FAIL could not extract any 'routing' filter globs from the workflow")

    # 2. COUNTERFEIT TABLE — against the workflow's own extracted globs, so a
    # filter regression fails HERE even if someone edits only the workflow.
    t_ok, t_msgs = run_counterfeit_table(wf_paid, wf_routing)
    msgs.extend(t_msgs)
    ok = ok and t_ok

    # 3. AUDIT REPORT — both outcomes must be announced for both legs.
    for marker, what in (
        ("behavioral tier EVALUATED for", "behavioral leg announces EVALUATED"),
        ("behavioral tier SKIPPED for", "behavioral leg announces SKIPPED"),
        ("routing tier EVALUATED", "routing leg announces EVALUATED"),
        ("routing tier SKIPPED", "routing leg announces SKIPPED"),
    ):
        if marker in text:
            msgs.append(f"PASS {what}")
        else:
            ok = False
            msgs.append(f"FAIL {what} — marker '{marker}' missing from the workflow; "
                        "green would be indistinguishable from not-exercised")
    return ok, msgs


def _self_test():
    passed = True

    def check(name, cond):
        nonlocal passed
        print(f"  {'PASS' if cond else 'FAIL'} {name}")
        passed = passed and cond

    # Glob semantics the filters rely on.
    check("** crosses directories",
          bool(glob_to_regex("plugins/x/skills/**/SKILL.md").match("plugins/x/skills/a/b/SKILL.md")))
    check("a/**/b also matches a/b",
          bool(glob_to_regex("plugins/x/skills/**/SKILL.md").match("plugins/x/skills/SKILL.md")))
    check("trailing /** matches anything under",
          bool(glob_to_regex("plugins/x/hooks/**").match("plugins/x/hooks/deep/gate.sh")))
    check("* does not cross a slash",
          not glob_to_regex("plugins/*/AGENTS.md").match("plugins/a/b/AGENTS.md"))
    check("literal dots are literal",
          not glob_to_regex("plugins/x/AGENTS.md").match("plugins/x/AGENTSxmd"))

    # Extraction from a filters block.
    wf = (
        "      - uses: dorny/paths-filter@v3\n"
        "        with:\n"
        "          filters: |\n"
        "            paid:\n"
        "              - 'plugins/${{ matrix.plugin }}/evals/promptfoo/**'\n"
        "              - 'evals/paid/**'\n"
        "            routing:\n"
        "              - 'evals/routing/**'\n"
    )
    check("extracts paid globs",
          extract_filter_globs(wf, "paid") ==
          ["plugins/${{ matrix.plugin }}/evals/promptfoo/**", "evals/paid/**"])
    check("extracts routing globs",
          extract_filter_globs(wf, "routing") == ["evals/routing/**"])

    # The RQ-001 counterfeit must go RED against the PRE-FIX filter shape
    # (promptfoo pack + shared harness only) and GREEN against the fixed shape.
    old_paid = ["plugins/${{ matrix.plugin }}/evals/promptfoo/**", "evals/paid/**"]
    old_routing = ["evals/routing/**", "plugins/*/skills/*/SKILL.md", ".claude-plugin/marketplace.json"]
    old_ok, _ = run_counterfeit_table(old_paid, old_routing)
    check("counterfeit table goes RED on the pre-fix filters", not old_ok)
    new_paid = [
        "plugins/${{ matrix.plugin }}/skills/**/SKILL.md",
        "plugins/${{ matrix.plugin }}/skills/**/references/**",
        "plugins/${{ matrix.plugin }}/commands/**",
        "plugins/${{ matrix.plugin }}/AGENTS.md",
        "plugins/${{ matrix.plugin }}/hooks/**",
        "plugins/${{ matrix.plugin }}/.claude-plugin/plugin.json",
        "plugins/${{ matrix.plugin }}/evals/promptfoo/**",
        "evals/paid/**",
    ]
    new_routing = [
        "evals/routing/**",
        "plugins/*/skills/**/SKILL.md",
        "plugins/*/.claude-plugin/plugin.json",
        ".claude-plugin/marketplace.json",
    ]
    new_ok, new_msgs = run_counterfeit_table(new_paid, new_routing)
    if not new_ok:
        for m in new_msgs:
            if m.startswith("FAIL"):
                print(f"    {m}")
    check("counterfeit table goes GREEN on the behavior-surface filters", new_ok)

    # Malformed spec raises rather than passing silently.
    try:
        _validate_spec({"plugin_behavior_paths": [], "routing_paths": ["x"]})
        check("empty plugin_behavior_paths raises", False)
    except ValueError:
        check("empty plugin_behavior_paths raises", True)

    print("self-test:", "OK" if passed else "FAILED")
    return 0 if passed else 1


def _validate_spec(spec):
    """Validation half of load_spec, for self-test without touching disk."""
    plugin_paths = spec.get("plugin_behavior_paths")
    routing_paths = spec.get("routing_paths")
    if not isinstance(plugin_paths, list) or not plugin_paths:
        raise ValueError("plugin_behavior_paths must be a non-empty list")
    if not isinstance(routing_paths, list) or not routing_paths:
        raise ValueError("routing_paths must be a non-empty list")
    return plugin_paths, routing_paths


def main(argv):
    if "--self-test" in argv:
        return _self_test()
    if "--repo" in argv:
        repo_root = argv[argv.index("--repo") + 1]
        ok, msgs = check_repo(repo_root)
        for line in msgs:
            print(f"  {line}")
        return 0 if ok else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
