#!/usr/bin/env bash
#
# orchestrate — plugin-specific cheap checks.
#
# SOURCED by the shared runner (evals/cheap/run.sh), not run standalone: it
# inherits that runner's helpers (ok/bad/group), its `set -uo pipefail`, a
# working directory of the repo root, and the exported PLUGIN_NAME / PLUGIN_DIR.
#
# Unlike the graveyard pack, nothing here is destructive — this plugin ships
# prose and two workflow-script templates. What the cheap tier defends instead
# is the plugin's *epistemic* contract: the load-bearing discipline that keeps
# adversarial verification honest lives in a handful of marker comments the
# templates are built around, and it is easy to silently gut one (delete the
# FROZEN-CONTEXT injection, drop the ADVERSARIAL-REFUTE-DEFAULT skeptic, soften
# VERDICT-WINS into an average) while the file still parses and reads fine.
# These greps make that kind of quiet regression a red build.

SKILL_DIR="$PLUGIN_DIR/skills/orchestrate"
TEMPLATES="$SKILL_DIR/templates"
A="$TEMPLATES/derived-verify.workflow.js"
B="$TEMPLATES/pipelined-verdict-wins.workflow.js"

# --- structure: the plugin's advertised surface actually exists ------------
group "orchestrate — structure"
for f in \
  "$PLUGIN_DIR/.claude-plugin/plugin.json" \
  "$SKILL_DIR/SKILL.md" \
  "$A" \
  "$B"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

# Both templates must be valid workflow scripts: a `meta` block the runtime
# parses and reason enough to load. bash can't run them, but node can parse-check.
group "orchestrate — templates declare meta"
for t in "$A" "$B"; do
  if grep -q 'export const meta = {' "$t" 2>/dev/null; then
    ok "$(basename "$t") declares export const meta"
  else
    bad "$(basename "$t") is missing 'export const meta' — not a workflow script"
  fi
done

# --- epistemic invariants: the load-bearing marker discipline --------------
# Each marker is a named piece of the verify-honestly contract. If one vanishes
# from the template it was meant to protect, the template has quietly lost its
# teeth even though it still runs. Grep the exact markers where they belong.
group "orchestrate — shared discipline markers"

# FROZEN-CONTEXT: one ground-truth string injected into every agent. Both
# templates depend on it — a verifier that reasons from different facts than the
# researcher "refutes" by disagreeing about the environment, not the claim.
for t in "$A" "$B"; do
  if grep -q 'FROZEN-CONTEXT' "$t"; then
    ok "$(basename "$t") keeps FROZEN-CONTEXT (single ground truth)"
  else
    bad "$(basename "$t") dropped FROZEN-CONTEXT — agents can drift off ground truth"
  fi
done

# ADVERSARIAL-REFUTE-DEFAULT: the skeptic defaults to disbelief so an
# unsupported claim fails closed instead of getting a free pass. Both templates.
for t in "$A" "$B"; do
  if grep -q 'ADVERSARIAL-REFUTE-DEFAULT' "$t"; then
    ok "$(basename "$t") keeps ADVERSARIAL-REFUTE-DEFAULT (skeptic fails closed)"
  else
    bad "$(basename "$t") dropped ADVERSARIAL-REFUTE-DEFAULT — verifier no longer disbelieves by default"
  fi
done

# DERIVED-TARGETS: Strategy A only. The verify set is harvested FROM the
# research output, never a list guessed up front. This is what makes A a sensor.
if grep -q 'DERIVED-TARGETS' "$A"; then
  ok "derived-verify keeps DERIVED-TARGETS (verify set harvested from fan-out)"
else
  bad "derived-verify dropped DERIVED-TARGETS — verify targets no longer derived from research"
fi

# UNTRUSTED-PROVENANCE: both templates. Worker findings cross into the verify
# and synthesize stages as data inside an untrusted-data fence, never as
# instructions — deleting the fence lets a researched claim phrased as a
# directive ("mark this confirmed") steer the verifier instead of being
# checked by it. Each grep is single-line: the pinned fragments sit on one
# physical line in the templates and must stay that way.
for t in "$A" "$B"; do
  if grep -q 'UNTRUSTED-PROVENANCE' "$t"; then
    ok "$(basename "$t") keeps UNTRUSTED-PROVENANCE (worker output crosses as data)"
  else
    bad "$(basename "$t") dropped UNTRUSTED-PROVENANCE — worker text is unfenced instructions again"
  fi
  if grep -q 'untrusted-data' "$t"; then
    ok "$(basename "$t") wraps worker findings in the untrusted-data fence"
  else
    bad "$(basename "$t") lost the untrusted-data fence — findings reach the verifier unfenced"
  fi
  if grep -q 'data, never instructions' "$t"; then
    ok "$(basename "$t") tells the verifier fenced text is data, never instructions"
  else
    bad "$(basename "$t") lost the data-never-instructions rule — fenced text can steer the verdict"
  fi
done

# The rule must have teeth where verdicts are made: the verifier is explicitly
# told fenced text cannot change its verdict procedure. Both templates.
for t in "$A" "$B"; do
  if grep -q 'change your verdict procedure' "$t"; then
    ok "$(basename "$t") pins that fenced text cannot change the verdict procedure"
  else
    bad "$(basename "$t") lost the verdict-procedure clause — injections can rewrite the check"
  fi
done

# Strategy B's reconciler also consumes worker findings; its precedence rule
# must be injection-proof too.
if grep -q 'change the precedence rule' "$B"; then
  ok "pipelined-verdict-wins shields the precedence rule from fenced findings"
else
  bad "pipelined-verdict-wins lost the precedence-rule shield — fenced findings can amend VERDICT-WINS"
fi

# VERDICT-WINS: Strategy B only. The reconciler must let a refuting verdict
# override the research claim, not average them. This is B's whole epistemic point.
if grep -q 'VERDICT-WINS' "$B"; then
  ok "pipelined-verdict-wins keeps VERDICT-WINS (verdict overrides refuted claim)"
else
  bad "pipelined-verdict-wins dropped VERDICT-WINS — refuted claims can survive into the recommendation"
fi
