#!/usr/bin/env bash
#
# check-testing-doc.sh — testing-doc drift guard (issue #89, standing order).
#
# docs/testing.md is the authoritative inventory of every eval tier, CI
# workflow job, and per-plugin eval pack kind. Documentation that isn't
# enforced drifts, so — same pattern as the roster-sync and branch-protection
# guards — the doc is VERIFIED, never trusted:
#
#   FORWARD: the live inventory is derived dynamically here (workflow job
#     names parsed from .github/workflows/*.yml, eval pack directories from
#     evals/*/ and the distinct pack kinds under plugins/*/evals/*/) and every
#     derived entry must appear in the doc's machine-readable inventory block.
#   REVERSE: every entry the doc's inventory block names must still exist in
#     the live inventory — the doc can never describe a tier that no longer
#     exists.
#
# The machine-readable block in docs/testing.md sits between the markers
#   <!-- BEGIN LIVE-INVENTORY ... -->  and  <!-- END LIVE-INVENTORY -->
# and carries one `kind: value` line per entry. Matrix-leg job names are
# normalized by stripping their `${{ ... }}` expression suffix, so the doc
# stays readable while the comparison stays exact.
#
# Usage:
#   evals/cheap/check-testing-doc.sh            # verify (exit 0 in sync, 1 drift)
#   evals/cheap/check-testing-doc.sh --print    # emit the live inventory lines
#                                               # (paste into the doc's block)
#
# Wired into evals/cheap/run.sh as a REPO-level gate: inert in a root without
# evals/counterfeits/ (the counterfeit tier's synthetic root, which does copy
# .github/workflows/evals.yml but never the corpus), fail-closed on drift —
# including a MISSING docs/testing.md — in the real repo.
# FAIL substring: "testing-doc drift".
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

python3 - "$REPO_ROOT" "${1:-verify}" <<'PY'
import glob, os, re, sys

root, mode = sys.argv[1], sys.argv[2]
DOC = os.path.join(root, "docs", "testing.md")
BEGIN = "<!-- BEGIN LIVE-INVENTORY"
END = "<!-- END LIVE-INVENTORY"
KINDS = ("workflow", "job", "eval-dir", "plugin-pack")

# ---- derive the live inventory (dynamic — never a hardcoded list) ----------
live = set()

# 1. Workflows and the display name of every job they define. A job's display
#    name is its job-level `name:` (4-space indent in this repo's workflows;
#    step names sit deeper and carry a `- ` prefix, workflow name sits at col 0),
#    falling back to the job id when no name is set. `${{ ... }}` matrix
#    expressions are stripped so per-plugin legs normalize to one stable name.
for wf in sorted(glob.glob(os.path.join(root, ".github", "workflows", "*.yml"))):
    live.add(f"workflow: {os.path.basename(wf)}")
    in_jobs = False
    job_id, job_name = None, None
    def flush():
        if job_id is None:
            return
        display = job_name if job_name else job_id
        display = re.sub(r"\s*\(\$\{\{[^}]*\}\}\)", "", display)
        display = re.sub(r"\$\{\{[^}]*\}\}", "", display).strip()
        live.add(f"job: {display}")
    for line in open(wf, encoding="utf-8"):
        line = line.rstrip("\n")
        if re.match(r"^jobs:\s*(#.*)?$", line):
            in_jobs = True
            continue
        if in_jobs and re.match(r"^\S", line):
            flush(); job_id, job_name = None, None
            in_jobs = False
        if not in_jobs:
            continue
        m = re.match(r"^  ([A-Za-z0-9_-]+):\s*(#.*)?$", line)
        if m:
            flush()
            job_id, job_name = m.group(1), None
            continue
        m = re.match(r"^    name:\s*(.+?)\s*$", line)
        if m and job_id is not None and job_name is None:
            job_name = m.group(1).strip("'\"")
    flush()

# 2. Repo-level eval pack directories.
for d in sorted(glob.glob(os.path.join(root, "evals", "*", ""))):
    live.add(f"eval-dir: evals/{os.path.basename(d.rstrip('/'))}")

# 3. Per-plugin eval pack KINDS (the distinct tier directories plugins ship —
#    e.g. cheap, promptfoo, pier, scale). Kinds, not per-plugin paths: adding a
#    plugin with an existing pack kind is routine and must not trip this guard;
#    inventing or retiring a pack KIND re-scopes the tier map and must.
for d in sorted(glob.glob(os.path.join(root, "plugins", "*", "evals", "*", ""))):
    live.add(f"plugin-pack: {os.path.basename(d.rstrip('/'))}")

if mode == "--print":
    for line in sorted(live):
        print(line)
    sys.exit(0)

# ---- parse the doc's machine-readable inventory block -----------------------
if not os.path.isfile(DOC):
    print(f"  FAIL testing-doc drift: {os.path.relpath(DOC, root)} does not exist "
          f"but the repo defines {len(live)} live inventory entries")
    sys.exit(1)
text = open(DOC, encoding="utf-8").read()
if BEGIN not in text or END not in text:
    print("  FAIL testing-doc drift: docs/testing.md has no LIVE-INVENTORY block "
          "(markers missing) — the doc cannot be verified against the live tiers")
    sys.exit(1)
block = text.split(BEGIN, 1)[1].split(END, 1)[0]
documented = set()
for line in block.splitlines():
    line = line.strip()
    m = re.match(r"^(%s):\s*(.+)$" % "|".join(KINDS), line)
    if m:
        documented.add(f"{m.group(1)}: {m.group(2).strip()}")

# ---- compare, both directions ----------------------------------------------
fail = 0
for entry in sorted(live - documented):
    print(f"  FAIL testing-doc drift: live '{entry}' is not in docs/testing.md's "
          f"inventory block — update the doc in this same PR (standing order)")
    fail += 1
for entry in sorted(documented - live):
    print(f"  FAIL testing-doc drift: docs/testing.md names '{entry}' which no "
          f"longer exists — remove or rename it in this same PR (standing order)")
    fail += 1
if fail == 0:
    print(f"  PASS docs/testing.md inventory block matches all {len(live)} live "
          f"entries (workflows, jobs, eval dirs, pack kinds), both directions")
sys.exit(1 if fail else 0)
PY
