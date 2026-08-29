# .redgate/INDEX.md — the verifier corpus index (GENERATED; do not edit)
#
# Built by plugins/redgate/skills/criteria-contract/scripts/criteria-index.sh.
# ARM consults this before writing check_cmds: a checkable shape from a prior
# run is a candidate positive control — open that run's CRITERIA.md for the
# actual check_cmd. A demoted shape stayed green under mutation control
# (WITNESS-in-fact) and must NOT be reused as proof.

| run | # | status | layers | statement |
|---|---|---|---|---|
| slice2-reconcile-r2 | 1 | checkable | script, protocol | POSITIVE CONTROL — an untampered passing run verifies green |
| slice2-reconcile-r2 | 2 | checkable | script, protocol | CHECKER drift on an otherwise-PASSING run fails the run |
| slice2-reconcile-r2 | 3 | checkable | script, protocol | CRITERIA drift on an otherwise-PASSING run fails the run |
| slice2-reconcile-r2 | 4 | checkable | protocol, report | The drift verdict is distinguishable from an ordinary unmet criterion |
| slice2-reconcile | 1 | checkable | script | reconcile.sh exists and is a parseable bash program |
| slice2-reconcile | 2 | checkable | script, protocol | An UNPINNED run is refused — you cannot verify what was never ratified |
| slice2-reconcile | 3 | demoted | script, protocol | check.sh drift after pinning fails the run |
| slice2-reconcile | 4 | demoted | script, protocol | CRITERIA.md drift after pinning fails the run |
| slice2-reconcile | 5 | checkable | script, protocol, report | A clean pinned run yields a per-criterion verdict table with evidence proof |
| slice2-reconcile | 6 | checkable | script, protocol | A PASS whose evidence file is missing or stale is rejected, not trusted |
| slice3-hooks | 1 | checkable | config | hooks.json exists and is valid JSON declaring PreToolUse and SessionStart |
| slice3-hooks | 2 | checkable | script | Both handlers exist and parse as bash |
| slice3-hooks | 3 | checkable | script, protocol | The guard DENIES a write to a pinned run's CRITERIA.md during MIDDLE |
| slice3-hooks | 4 | checkable | script, protocol | The guard ALLOWS the same write while the run is still in BEGIN |
| slice3-hooks | 5 | checkable | script | The guard is indifferent to paths outside .redgate/ |
| slice3-hooks | 6 | checkable | prose | hooks prose carries a portability caveat (hooks are Claude-Code-only) |
| slice4-references | 1 | checkable | docs | All three reference docs exist under the driver skill |
| slice4-references | 2 | checkable | docs | SKILL.md links every reference (progressive disclosure actually wired) |
| slice4-references | 3 | checkable | docs | recursion-contract carries all four spawn-precondition parts and the termination rule |
| slice4-references | 4 | checkable | docs | handoff-envelope states the cap rule that excludes criteria text |
| slice4-references | 5 | checkable | docs | round-types carries a shape-criteria template for every round type |
| slice5-growth | 1 | checkable | plugin, marketplace | recurrence-detector ships as a registered marketplace plugin |
| slice5-growth | 2 | checkable | prose, protocol | Its invariant forbids auto-scaffolding — DETECT proposes, the human and factory dispose |
| slice5-growth | 3 | checkable | prose | Its invariant requires a threshold of sightings before a candidate is surfaced |
| slice5-growth | 4 | checkable | docs | consolidate-delta lands on BOTH memory plugins (episodic and semantic) |
| slice5-growth | 5 | checkable | docs | The delta discipline names the typed operations that make recurrence greppable |
| slice5-growth | 6 | checkable | docs | judge-calibration codifies the negative-control contract for judged verifiers |
| slice5-growth | 7 | checkable | plugin, ci | The new plugin passes the marketplace's own structural gate in isolation |
