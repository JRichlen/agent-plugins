# Cheap eval pack for the 'eval-ladder' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE and
# $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: the invariant that no eval result is reported as evidence
# beyond what its tier structurally proves. Three clauses carry that weight and
# are the ones a well-meaning edit is most likely to soften:
#   (a) every rung declares what it structurally CANNOT prove,
#   (b) a judge is bounded by TPR/TNR against held-out human labels — never by
#       raw agreement, which lies under class imbalance,
#   (c) an irreversible-action scenario is scored pass^k, never a majority.
# These checks are paranoid about those three. Wording drift elsewhere is not
# what this tier catches — that is the behavioral tier's and the demo's job.

SKILL="$PLUGIN_DIR/skills/eval-ladder/SKILL.md"
AGENTS="$PLUGIN_DIR/AGENTS.md"
CMD="$PLUGIN_DIR/commands/eval-ladder.md"
REFS="$PLUGIN_DIR/skills/eval-ladder/references"

group "eval-ladder — structure"
for f in "$PLUGIN_DIR/.claude-plugin/plugin.json" "$SKILL" "$AGENTS" "$PLUGIN_DIR/README.md" "$CMD" \
         "$REFS/eval-surfaces.md" "$REFS/judge-alignment.md" "$REFS/metric-choice.md" \
         "$REFS/integrity-hazards.md" "$REFS/source-map.md"; do
  if [ -f "$f" ]; then ok "present: $f"; else bad "MISSING: $f"; fi
done

group "eval-ladder — invariant survives verbatim"
INV='never on a k-of-N majority'
has "$SKILL"  "$INV" "SKILL.md carries the pass^k clause verbatim" "SKILL.md lost the pass^k clause"
has "$AGENTS" "$INV" "AGENTS.md carries the pass^k clause verbatim" "AGENTS.md lost the pass^k clause"
hasE "$SKILL" 'every green is reported with its blind spot' "SKILL.md requires the blind spot beside every green" "SKILL.md no longer requires the blind spot beside every green"
hasE "$SKILL" 'bounded by that judge.s measured TPR/TNR' "SKILL.md bounds judge verdicts by measured TPR/TNR" "SKILL.md no longer bounds judge verdicts by TPR/TNR"

group "eval-ladder — every rung declares what it cannot prove"
hasE "$SKILL" 'Structurally cannot' "the ladder table has a 'structurally cannot' column" "the ladder table lost its 'structurally cannot' column"
# The table is the load-bearing artifact: eight rungs, each with a non-empty
# cannot-prove cell. Count the rows so deleting one goes red here.
RUNGS="$(grep -cE '^\| [0-7] \| \*\*' "$SKILL" || true)"
if [ "$RUNGS" -eq 8 ]; then
  ok "all 8 rungs (0-7) present in the ladder table"
else
  bad "ladder table has $RUNGS rungs, expected 8 (0-7) — a rung was added or dropped without updating this check"
fi
hasE "$SKILL" 'A tier that cannot answer #2 or #5 is decoration' "the audit procedure refuses tiers with no stated blind spot" "the audit procedure no longer refuses tiers with no stated blind spot"

group "eval-ladder — bottom-up ordering is stated before the ladder"
hasE "$SKILL" 'bottom-up from observed failures' "SKILL.md orders construction bottom-up from observed failures" "SKILL.md lost the bottom-up ordering rule"
hasE "$SKILL" 'Descend before you ascend' "SKILL.md forbids buying a judge for what a predicate can decide" "SKILL.md lost the descend-before-ascend rule"
hasE "$SKILL" 'closest to the harm' "SKILL.md requires grading the surface closest to the harm" "SKILL.md lost the closest-to-the-harm rule"

group "eval-ladder — judge validation refuses raw agreement"
hasE "$REFS/judge-alignment.md" 'Never report raw agreement' "judge-alignment forbids raw agreement as the judge metric" "judge-alignment no longer forbids raw agreement"
hasE "$REFS/judge-alignment.md" 'TPR' "judge-alignment requires TPR" "judge-alignment lost TPR"
hasE "$REFS/judge-alignment.md" 'TNR' "judge-alignment requires TNR" "judge-alignment lost TNR"
hasE "$REFS/judge-alignment.md" 'self-agreement is the label-noise floor|self-agreement.*noise floor|noise floor of the whole tier' "judge-alignment names self-agreement as the noise floor" "judge-alignment lost the self-agreement noise floor"
hasE "$REFS/judge-alignment.md" '[Bb]inary, always|Binary over Likert|not 1.5' "judge-alignment requires binary verdicts" "judge-alignment no longer requires binary verdicts"

group "eval-ladder — metric choice keeps the irreversible-action floor at 1.0"
hasE "$REFS/metric-choice.md" 'irreversible action' "metric-choice segments the floor by irreversibility" "metric-choice lost the irreversible-action row"
hasE "$REFS/metric-choice.md" '1\.0 \(pass\^k\)' "metric-choice pins the irreversible floor at 1.0 (pass^k)" "metric-choice no longer pins the irreversible floor at 1.0"
hasE "$REFS/metric-choice.md" 'FAULT is not FAIL|FAULT.*not.*FAIL' "metric-choice separates FAULT from FAIL" "metric-choice lost the FAULT/FAIL separation"
hasE "$REFS/metric-choice.md" 'fail closed on starvation|never tested' "metric-choice fails closed on starvation" "metric-choice no longer fails closed on starvation"
hasE "$REFS/metric-choice.md" 'must-not-fire' "metric-choice requires must-not-fire controls" "metric-choice lost the must-not-fire control requirement"
# The naive estimator must be named as forbidden, not merely omitted.
hasE "$REFS/metric-choice.md" 'Never report the naive' "metric-choice forbids the naive pass@k estimator" "metric-choice no longer forbids the naive pass@k estimator"

group "eval-ladder — between-tier hazards are all present"
for h in 'Tuning on the gate' 'Criteria drift' 'Saturation' 'Missing controls' \
         'The harness confound' 'Contamination' 'Offline is not online'; do
  hasE "$REFS/integrity-hazards.md" "$h" "hazard documented: $h" "hazard dropped from integrity-hazards.md: $h"
done

group "eval-ladder — provenance is checkable, not asserted"
hasE "$REFS/source-map.md" 'awesome-evals' "source-map names the corpus it was distilled from" "source-map lost its corpus attribution"
hasE "$REFS/source-map.md" 'open the primary source and confirm' "source-map tells the reader to confirm load-bearing claims at the source" "source-map lost its confirm-at-the-source caveat"
# Every rule section must carry at least one resolvable primary-source URL.
SRC_URLS="$(grep -cE '<https?://' "$REFS/source-map.md" || true)"
if [ "$SRC_URLS" -ge 20 ]; then
  ok "source-map carries $SRC_URLS primary-source URLs"
else
  bad "source-map carries only $SRC_URLS primary-source URLs (expected >= 20) — provenance was thinned"
fi

group "eval-ladder — disambiguated from siblings"
has "$SKILL" 'hypothesis, not a measurement' "SKILL.md refuses to call an unvalidated suite a measurement" "SKILL.md lost the hypothesis-not-measurement line"
hasE "$SKILL" 'Never write .fully tested.' "SKILL.md forbids reporting 'fully tested'" "SKILL.md no longer forbids reporting 'fully tested'"
hasE "$CMD" 'never report .fully tested.' "command restates the reporting rule" "command lost the reporting rule"
