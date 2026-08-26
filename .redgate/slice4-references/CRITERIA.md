# CRITERIA — slice 4: the protocol references (consolidation round)

<!-- Derived from approved plan slice 4. Prose-only; the verifier checks the
     SHAPE a reviewable reference must have (progressive-disclosure wiring +
     the operational content each doc must carry), which is the research-round
     verifier pattern applied to a docs slice. -->

## #1 All three reference docs exist under the driver skill
layers: docs
red-because: absent — the references directory does not exist
check_cmd: R=../../plugins/redgate/skills/redgate/references; test -f $R/round-types.md && test -f $R/handoff-envelope.md && test -f $R/recursion-contract.md

## #2 SKILL.md links every reference (progressive disclosure actually wired)
layers: docs
red-because: absent — nothing links them
check_cmd: S=../../plugins/redgate/skills/redgate/SKILL.md; grep -q 'references/round-types.md' $S && grep -q 'references/handoff-envelope.md' $S && grep -q 'references/recursion-contract.md' $S

## #3 recursion-contract carries all four spawn-precondition parts and the termination rule
layers: docs
red-because: absent — the doc does not exist
check_cmd: F=../../plugins/redgate/skills/redgate/references/recursion-contract.md; grep -qi 'named seam' $F && grep -qi 'sub-criteria' $F && grep -qi 'depth_remaining' $F && grep -qi 'child pool\|sibling' $F

## #4 handoff-envelope states the cap rule that excludes criteria text
layers: docs
red-because: absent — the doc does not exist
check_cmd: F=../../plugins/redgate/skills/redgate/references/handoff-envelope.md; grep -qi 'verbatim' $F && grep -qi 'excluded from the cap\|excludes criteria\|not counted' $F

## #5 round-types carries a shape-criteria template for every round type
layers: docs
red-because: absent — the doc does not exist
check_cmd: F=../../plugins/redgate/skills/redgate/references/round-types.md; for t in orientation plan build consolidation; do grep -qi "$t" $F || exit 1; done; grep -qc 'check_cmd:' $F >/dev/null && [ "$(grep -c 'check_cmd:' $F)" -ge 4 ]
