# CRITERIA — slice 5: the growth loop (recurrence-detector + amendments)

<!-- Derived from approved plan slice 5. The DETECT organ was named in the
     protocol as the missing step that closes EMIT -> CONSOLIDATE -> DETECT ->
     SCAFFOLD -> GATE -> LOAD. -->

## #1 recurrence-detector ships as a registered marketplace plugin
layers: plugin, marketplace
red-because: absent — the plugin does not exist
check_cmd: test -f ../../plugins/recurrence-detector/skills/recurrence-detector/SKILL.md && python3 -c "import json,sys; m=json.load(open('../../.claude-plugin/marketplace.json')); sys.exit(0 if any(p['name']=='recurrence-detector' for p in m['plugins']) else 1)"

## #2 Its invariant forbids auto-scaffolding — DETECT proposes, the human and factory dispose
layers: prose, protocol
red-because: absent — no invariant is stated anywhere
check_cmd: F=../../plugins/recurrence-detector/skills/recurrence-detector/SKILL.md; grep -qi 'NEVER auto-scaffold\|never auto-scaffolded' $F && grep -qi 'cited\|citation\|sightings' $F

## #3 Its invariant requires a threshold of sightings before a candidate is surfaced
layers: prose
red-because: absent
check_cmd: F=../../plugins/recurrence-detector/skills/recurrence-detector/SKILL.md; grep -qiE 'seen (>=|at least) ?[0-9N]|threshold' $F

## #4 consolidate-delta lands on BOTH memory plugins (episodic and semantic)
layers: docs
red-because: absent — neither reference exists
check_cmd: test -f ../../plugins/dev-diary/skills/dev-diary/references/consolidate-delta.md && test -f ../../plugins/fleet-playbook-curator/skills/fleet-playbook-curator/references/consolidate-delta.md

## #5 The delta discipline names the typed operations that make recurrence greppable
layers: docs
red-because: absent
check_cmd: F=../../plugins/dev-diary/skills/dev-diary/references/consolidate-delta.md; grep -q 'ADD' $F && grep -q 'UPDATE' $F && grep -q 'REMOVE' $F && grep -qi 'failure-shape\|failure shape' $F

## #6 judge-calibration codifies the negative-control contract for judged verifiers
layers: docs
red-because: absent
check_cmd: F=../../plugins/plugin-factory/skills/plugin-factory/references/judge-calibration.md; grep -qi 'negative control\|calibration' $F && grep -qi 'one judge per dimension\|per dimension' $F

## #7 The new plugin passes the marketplace's own structural gate in isolation
layers: plugin, ci
red-because: absent — nothing to validate yet
check_cmd: cd ../.. && evals/cheap/install-smoke.sh recurrence-detector 2>/dev/null || python3 -c "import json,os,sys; d=json.load(open('plugins/recurrence-detector/.claude-plugin/plugin.json')); sys.exit(0 if d['name']=='recurrence-detector' and os.path.isdir('plugins/recurrence-detector/skills/recurrence-detector') else 1)"
