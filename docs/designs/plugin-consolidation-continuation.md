# Responsibility-first consolidation

Status: repository refactor in progress, not a live installation or a measured
behavioral improvement. Current source baseline:
`2ff596caf3be9fd59ebfe42d17b05ccab1f1da1d` (27 plugins, PR150 merged).

The earlier nine-bundle hypothesis is superseded as an implementation target.
Moving the same competing instructions into fewer folders would not remove
redundancy. Packaging follows canonical ownership, selected methods and the
host's actual capabilities.

## One owner per responsibility

[core/OPERATING.md](../../core/OPERATING.md) owns shared intent/scope/authority,
task-state and routing boundaries. [core/ownership.json](../../core/ownership.json)
indexes owners, activation classes, service entry/exit and returned evidence.

| Responsibility | Canonical owner | What disappears |
|---|---|---|
| Shared authority, interaction, state and routing | Core | Root/protocol/coordinator copies of the same governing rules |
| Briefs, dispatch, output ownership, integration and recovery | delegated-intelligence | Jori persona/board/tiers/observer and duplicate coordination doctrine |
| Persistent plans and dependencies | wayfinder | A second coordinator planning board |
| Diff scope | scope-fence | Protocol-specific scope doctrine |
| Action risk and restoration | semver-gate | Competing approval classifications |
| Outbound content | egress-gate | Repeated transmission policy in coordinators |
| Retry bounds and stop reports | stop-rule | Delegation's independent two-retry quota |
| Completion evidence | verify-before-claim | Coordinator self-confidence as a verification substitute |
| Selected executable acceptance checks | verify-before-claim / verify-work | Universal default rounds, calibration, recursive workflow and mandatory ledger ceremony |
| Continuity | context-handoff | Coordinator-specific cross-session policy |
| Learning candidates | recurrence-detector, with existing records | Automatic observers, schedules and silent instruction adoption |

Core supplies shared obligations without loading every procedure. Services return
evidence and limits to the caller. Playbooks own task methods; techniques are
bounded choices within them. Host adapters are reviewable projections, not
permission grants or proof that a host has been configured.

## Actual source-lineage map

Before 27 | After 24 | Net -3 (kept 24, merged-away 2, retired 1, new 0).

The verbs below describe source entities. Three public products disappear:
two have distinct useful mechanisms absorbed by surviving owners; the fleet
product retires without claiming a replacement.

| Before entity | Verb | Owner / destination | Disposition |
|---|---|---|---|
| graveyard | keep | Repository archival and guarded deletion | Distinct responsibility retained; callers reference shared core/services. |
| plugin-factory | keep | Plugin authoring | Distinct responsibility retained; callers reference shared core/services. |
| tailscale-wif | keep | Tailscale identity setup | Distinct responsibility retained; callers reference shared core/services. |
| fleet-playbook-curator | retire | No replacement product | Remove optional fleet deployment/curation package; preserve generic deltas and pinned history; external jobs untouched. |
| dev-diary | keep | Episodic work record | Distinct responsibility retained; callers reference shared core/services. |
| voice | keep | Presentation and explicitly requested review | Distinct responsibility retained; callers reference shared core/services. |
| grill-me | keep | Plan interview | Distinct responsibility retained; callers reference shared core/services. |
| tracer-bullets | keep | Retained end-to-end technique | Distinct responsibility retained; callers reference shared core/services. |
| semver-gate | keep | Risk classification and restoration | Distinct responsibility retained; callers reference shared core/services. |
| verify-before-claim | absorb | Claim checks and optional acceptance verification | Distinct executable pin/drift/freshness mechanisms join this owner; no universal lifecycle. |
| diagnosing-bugs | keep | Debugging playbook | Distinct responsibility retained; callers reference shared core/services. |
| docs-hygiene | keep | Instruction-file audit | Distinct responsibility retained; callers reference shared core/services. |
| context-handoff | keep | Continuity service | Distinct responsibility retained; callers reference shared core/services. |
| codebase-design | keep | Interface comparison | Distinct responsibility retained; callers reference shared core/services. |
| wayfinder | keep | Persistent decision/work plan | Distinct responsibility retained; callers reference shared core/services. |
| scope-fence | keep | Diff-scope procedure | Distinct responsibility retained; callers reference shared core/services. |
| find-before-build | keep | Existing-implementation search | Distinct responsibility retained; callers reference shared core/services. |
| egress-gate | keep | Outbound-content check | Distinct responsibility retained; callers reference shared core/services. |
| stop-rule | keep | Retry accounting and stopping | Distinct responsibility retained; callers reference shared core/services. |
| redgate | merge-into | verify-before-claim | Public product/default rounds retire; useful acceptance helpers survive behind verify-work and thin legacy adapters. |
| recurrence-detector | keep | Sourced learning proposals | Distinct responsibility retained; callers reference shared core/services. |
| jori | merge-into | delegated-intelligence | Public product retires; coordinator persona, tier ladder, board and observer duplication are deleted. |
| agent-compiler | keep | Versioned behavior composition | Distinct responsibility retained; callers reference shared core/services. |
| eval-ladder | keep | Evaluation design | Distinct responsibility retained; callers reference shared core/services. |
| consolidation-map | keep | Inventory/disposition accounting | Distinct responsibility retained; callers reference shared core/services. |
| wave-research | keep | Adversarial research playbook | Distinct responsibility retained; callers reference shared core/services. |
| delegated-intelligence | absorb | Delegated execution | One brief/dispatch/ownership/recovery method; core state and stop-rule limits are referenced. |

Reconciliation: 27 = 24 kept + 2 merged-away + 1 retired; 24 = 24 kept + 0 new.
Absorbing owners count as kept. Every source entity appears once and both merge
targets survive.

The preceding `0f0eb6f` inventory contained 26 plugins. PR150 added the delegation
service, producing this 27-entity baseline. Earlier prove-the-undo -> semver-gate
and orchestrate -> wave-research absorptions are historical inputs already inside
surviving owners, not extra entities to count again.

## Entry, exit and handoff

Core distinguishes explicit request, implied task match, dependency, state/risk,
always-on invariant and offer-only activation. Selection does not authorize
new effects. A method declares its inputs, evidence, dependency and exit; it
returns to the existing record instead of keeping a persona active afterward.

A documentation stage receives verified findings and remaining uncertainties
from debugging. A report is not upgraded to verified because it was pasted
into another stage. Stopped or blocked work still accounts for workers and
in-flight actions, including uncertain non-cancellable outcomes.

## Migration and compatibility

- [Coordination](../migrations/coordination.md): retire the old product identity,
  retain the existing delegation command, and review any old global fragment.
- [Verification](../migrations/verification.md): keep distinct acceptance helpers
  and protected contract behavior; legacy filesystem entry points are thin
  adapters rather than a second implementation.
- [Fleet](../retirements/fleet-playbook-curator.md): repository retirement leaves
  copied deployments, schedules, credentials and repositories alone.
- Generated selected-service core copies have source hashes. Always-on host
  adoption remains explicit; repository presence does not establish installation.
- Historical protocol documents and receipts are preserved as history, not live
  governing instructions. Deprecated notices explain the replacement.

## Evidence and rollout

Run structural, ownership, source-contract, kernel/integrity, routing, generator
and relevant regression checks. Mutate load-bearing clauses and guards rather
than preserving obsolete prose because an old test pinned it. Keep test validity
and blocked environmental prerequisites visible; never refresh frozen evidence
to hide host incompatibility.

The current full gate and Linux/host qualification remain requirements.
Thought experiments, static checks, shorter descriptions and smaller inventories
do not establish better outcomes or lower total cost. Compare factual accuracy,
task success, user steering, rework and accepted-work cost with a recorded baseline
before broader adoption.

The [synthetic re-entry pilot](conversation-reentry-pilot.md) remains exploratory.
PR129's frozen criteria and held-out corpus are untouched and do not validate
this refactor. Publication's approved automatic model checks do not authorize
manual paid suites or expanded budgets.

Keep changes isolated and reversible. Restore source, catalog, routing/coverage
and generated artifacts together; rehearse the restore. No global installation,
release, merge or deployed-job cleanup is part of this repository refactor.
