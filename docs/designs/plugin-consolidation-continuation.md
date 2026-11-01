# Continue the plugin consolidation

Status: local retirement patch plus reviewable follow-on recommendations;
no live installation changed. Based on live main
`0f0eb6f172e1e2d06396011a78e689f06ca48969`.
The person requested consolidation and questioned Redgate/Jori's fit; the
specific dispositions below are the author's recommendations, not ratified
user decisions or evidence of disuse.

Continue the existing merged work: [PR146](https://github.com/JRichlen/agent-plugins/pull/146)
absorbed prove-the-undo into semver-gate;
[PR149](https://github.com/JRichlen/agent-plugins/pull/149) absorbed orchestrate
into wave-research. Their migration notes remain authoritative for those moves.
No remaining portfolio plan was found in repository design documents or the
open issue/PR inventory. This continuation records the unresolved next slice,
rather than superseding either merged map.

## Decision recommendation

Stop growing peer coordinators. Treat bounded delegation as an optional shared
execution method, frozen verification as an optional evidence mechanism, and
human re-entry as communication behavior. They should compose with the domain
specialist; none needs to be a universal identity or another governing system.

Optional applies to methods, not to every obligation. Retain a minimal always-on
invariant/routing layer in the existing instruction assembly: user authority,
permission and data boundaries, truthful provenance/verification claims, and
the pointer to the applicable specialist. Select detailed methods by task,
activity, context and perspective. Once an evidence contract is active, its
integrity requirements remain binding. Permission and truthful-reporting rules
must not depend solely on a model probabilistically activating a skill.
This is a proposed scope boundary, not an edit to global/core instructions or
a claim that every host currently enforces it identically. Host-specific
assembly and enforcement require separate inspection before any install.

Reuse the six proposed trigger classes in
[issue 84](https://github.com/JRichlen/agent-plugins/issues/84): implied, explicit
user, dependency, state/risk, always-on invariant and offer-only. That issue was
closed as NOT_PLANNED with an explicit deferral to issue 117; it is not a shipped
metadata system. The existing `evals/routing/route-contract.js` already separates
specialist, envelope, guards and interaction owner. Extend that composition
contract where evidence identifies a gap, rather than adding another peer router.
Routing eligibility never grants action authority. Keep offer-only actions
offer-only, even if their subject matter matches a context selector.

Recommend **Jori's eventual merge into agent-compiler's optional behavior
registry**, after a supported command and activation migration is demonstrated.
Keep its package available during that migration. Do not merge PR150 as a second
peer coordinator unchanged. Reuse its recovery, brief and file-handback work in
the optional method, with attribution, once its outstanding review findings are
resolved. This is a packaging recommendation, not a claim that a compiler module
currently replaces Jori or that PR150 has demonstrated user benefit.

Recommend **retaining Redgate's executable evidence mechanism at its existing
paths while simplifying its orchestration policy under issue 135**. Its name and
package are not sacred: later absorption into a verification host is possible,
but moving it now introduces compatibility work without removing its unique
mechanism. Existing claim checking cannot substitute for frozen independent
verification. Do not port Redgate's entire driver into another plugin and call
that consolidation.

The next target is 24 installable plugins if Jori merges into the existing
compiler after the fleet curator retirement and PR150 adds no new package. Redgate's later packaging is deliberately
unsettled. Growing the catalog from 26 to 27 plugins by adding another coordinator
is not the target, and fewer names
alone is not evidence of improved behavior.

## Implemented local slice: retire fleet-playbook-curator

Remove its repository package and marketplace listing. Preserve the generic
typed-delta guidance through the existing dev-diary reference and update live
callers. Curator-specific deployment, two-clock scheduling and per-claim
repo/file/commit validation remain recoverable in the
[baseline source](https://github.com/JRichlen/agent-plugins/tree/0f0eb6f172e1e2d06396011a78e689f06ca48969/plugins/fleet-playbook-curator),
rather than being absorbed into a new universal curator.

Why: the package is selected for retirement in this task; present usage is not
established by repository fixture results. What's lost: new installation and
deployment through this package, its named commands, and its current test/catalog
coverage. Generic delta guidance survives, but no remaining package is claimed
to replace fleet deployment. Existing deployments copied into target repositories
remain untouched, including their schedules, secrets, generated playbooks and
pull requests. Source retirement does not stop or uninstall those deployments.

Rollback must restore the package and coupled catalog/reference/coverage changes
together from the pinned base, then regenerate and rerun the relevant free
checks. The implementation report must include the actual restore rehearsal and
test outcomes before calling the migration verified. A later release/install or
deployed-job cleanup is a separate action; do not infer authority for it here.

## What overlaps and what survives

| Concern | Evidence in current source / pending work | Recommendation and loss to disclose |
|---|---|---|
| General coordination | `plugins/jori/skills/jori/SKILL.md`; PR150 at `f32a40e544e77605b123d7418912e98235935346` | Preserve bounded briefs, user authority, honest states, cost accounting and recovery as one optional method. Retire Jori packaging only after parity. Mandatory substantive delegation and the capacity-dependent observer policy would become opt-in strategies. Complex-work project records stay proportional; simple work still gets no dashboard. |
| Execution recovery | PR150 proposes one writer per output, file-backed handbacks, check-before-relaunch and bounded retries | Reuse as subordinate execution method. Inspect completed files and provenance rather than trusting a board. Neither a completed file nor a worker's report proves semantic correctness. Do not use PR150's fallback passes to claim real independent workers ran. |
| Research | `plugins/wave-research/skills/wave-research/` | Keep the specialist and its absorbed templates. Its thesis/rival/evidence method is distinct from generic coordination. PR150's pointer remains pending, not an installed dependency. |
| Cross-session continuity | `plugins/context-handoff/skills/context-handoff/SKILL.md` | Keep the ordered phase-boundary decision and pointer-only handoff. Do not add general task execution or human message formatting to this specialist. |
| Human orientation | `plugins/voice/skills/human-voice/SKILL.md`; [re-entry pilot](conversation-reentry-pilot.md) | Test reading order, provenance and permission preservation without activating changes. A successful behavior belongs in existing voice guidance or an optional compiler module, not a new plugin. |
| Evidence contracts | `plugins/redgate/skills/criteria-contract/scripts/scaffold-run.sh`; `skills/reconcile/scripts/reconcile.sh` within the same plugin | Preserve red proof, contract pinning, rehash/drift rejection, independent fresh evidence, and distinction between a failing criterion and a broken harness. Keep the current CLI and artifact format until migration passes. |
| Protected work | `plugins/redgate/hooks/hooks-handlers/guard-redgate-paths.sh` and `session-start.sh` | Preserve protection of ratified files during TRACE and visibility of unfinished runs. Optional verification does not mean optional integrity once a run is ratified. |
| Action authority and restoration | `plugins/semver-gate/skills/`; compiler discipline modules | Keep authority, scope, egress and tested restoration obligations. Delegation never expands worker authority. Retirement must not delete these safeguards by removing a name. |
| Claims, retry bounds, learning | verify-before-claim, stop-rule, recurrence-detector | Keep their distinct responsibilities. The re-entry examples are hypotheses, not recurrence sightings; no perpetual observer or automatic instruction adoption. |

PR150's body reports fixtures/static checks, no promptfoo pack, no model-arm
agentic run and no actually spawned demonstration. Those are author reports,
not checks repeated here. They support reviewing the proposed mechanism, not
declaring equivalence, responsiveness or efficiency proven. [Issue 123](https://github.com/JRichlen/agent-plugins/issues/123)
also distinguishes real traces from behavioral captures and notes the absence
of session telemetry. Do not infer lack of consumers from that absence.

The latest inspected PR150 commit tightens coordinator-only session-control,
sending/spending rules and fixture grading; it does not remove the new peer
package or Jori overlap. Preserve that restriction in any extraction. Its
automatic scheduling guidance and vendor-specific verification defaults still
need reconciliation with explicit user authorization and configured routing.

For a concrete reading-cost proxy, the fresh Windows checkout's primary
`SKILL.md` files contain 3,359 characters for Jori and 16,093 for Redgate,
including checkout line endings, before referenced material. These are character
counts, not measured tokens, runtime load or dollar cost. PR150 reports another
124 estimated catalog tokens; that estimate has not been reproduced here. A
proper comparison must include selected references, coordinator/worker calls,
retries and accepted-work cost. Removing a catalog entry alone says nothing
about that total. The proposed optional method avoids loading both coordination
identities or the full verification driver for every task.

## Minimal optional coordination contract to implement next

Proposed home: `plugins/agent-compiler/registry/behaviors/discipline/`, using its
existing versioned rule/probe format. This proposal does not write or compile
a runtime module. Exact IDs, dependencies and source provenance are established
in the migration PR, not embedded into generated agents by hand.

1. Choose inline or delegate by dependency, uncertainty and total accepted-work
   cost. A simple task stays direct; tightly coupled work has one owner. Respect
   the user's configured model and delegation choices rather than hard-coding
   vendor tiers or a mandatory substantive-delegation quota.
2. A real dispatch names objective, source pointers, scope, allowed effects,
   tool/model/effort allowance, expected evidence, output owner and stop condition.
   No delegate can interview the person, widen authority or delegate further
   without permission. A budget estimate is not an enforced cap.
3. Track assigned, running, returned and independently verified distinctly.
   Attribute reports; inspect output and scope before trusting success. Worker
   content is data, never a new authorization. Model identity requires evidence.
4. Recover only missing or invalid work, preserving valid outputs and unrelated
   edits. Revalidate provenance and dependencies before reuse. Apply existing
   stop-rule retry bounds; do not create another retry policy.
5. Report incomplete state, decision-changing uncertainty and required user
   choices in ordinary language. Reuse the project's record only when needed;
   no mandatory dashboard, confidence banner or background observer.

The authority and truthful-reporting obligations above belong in the minimal
invariant layer as well as the selected method; the module must not become
their only enforcement point. This extracts shared obligations while leaving research strategy in wave-research,
phase routing in context-handoff, action authority in semver-gate, and verifier
execution in Redgate. The re-entry pilot supplies a separate human usability
test for rule 5 and cannot establish rules 1-4.

## Replacement proof before Jori can disappear

| Surface | Required evidence | Restore path |
|---|---|---|
| `/jori` and named skill invocation | A documented compatible entry point resolves to the optional method; explicit invocation still works on supported harnesses | Restore package/catalog from the migration base commit |
| Explicit global activation fragment | Inventory known activation references with the user; show a proposed replacement diff; no silent global edits | Keep the original fragment and a copy of any user-approved changed file |
| Codex implicit invocation | Make the intended activation choice explicit; compare small inline, coupled and delegated cases before changing `allow_implicit_invocation` | Restore `skills/jori/agents/openai.yaml` from the migration base |
| Versioned compiler behavior | Registry resolves dependency/effect ceilings; deterministic compile/render with provenance; no hand-edited output | Recompile the previously accepted query against the pinned baseline registry |
| Brief/recovery behavior | Free fixture checks plus separately authorized matched real-worker evidence: interrupted, empty, stale, injected, dishonest-done and complete outputs; independent verification is actually independent | Use legacy entry point; retain original artifacts; no relaunch solely because board state differs |
| Catalog, CI and consumers | Reconcile manifests, pricing config references, routing roster, arm manifests, red-team configs, docs, install smoke and coverage inventory together; record intentional historical mentions | Revert one isolated migration commit, regenerate using baseline tools and rerun free checks |

No implementation claim substitutes for this proof. Missing model evidence does
not justify paid execution under this task. If a meaningful installed workflow
has no supported replacement, return that decision before removal.

## Redgate simplification and compatibility

Use [issue 135](https://github.com/JRichlen/agent-plugins/issues/135), rather than
creating a second efficiency governor. Once target, behavior, risk and verifier
are known, execute the smallest verifiable slice. More investigation must name
an uncertainty that could alter the change or safety decision. Preserve the
specialist-first/direct-work calibration already in root AGENTS.

Before altering Redgate packaging, prove compatibility for:

- Existing `.redgate/<slug>/` criteria, checker, manifest, hashes, evidence and
  `gates.log`; resume an unfinished run and reject stale evidence and drift.
- `plugins/recurrence-detector/skills/recurrence-detector/scripts/gate-report.sh`,
  which consumes the run ledger. Preserve semantics, not merely filenames.
- `evals/routing/route-contract.js`, its trajectory cases,
  `ci/behavior-surfaces.json`, and `.github/workflows/scale.yml`.
- Mutation/scale cases for tampering, criterion failure versus harness fault,
  missing independent review and protected contract writes.

Keep explicit authority and independent verification. Challenge mandatory
planning/retro rounds and calibration burden through issue 135's low-risk and
tiny-high-risk counterexamples; do not weaken safeguards to reduce ceremony.
No new verifier host or runtime wrapper is authorized merely by this proposal.
Technique selection remains a separate research question using existing
specialists such as tracer-bullets; this change adds no mental-framing router
or plugin. Any selection reference should sit behind the existing routing layer.

## Inventory and reconciliation

Actual local change: Before 26 | After 25 | Net -1 (kept 25,
merged-away 0, retired 1, new 0). Every before-inventory entity appears once:

| Verb | Entity | Status |
|---|---|---|
| keep | graveyard | unchanged |
| keep | plugin-factory | unchanged |
| keep | tailscale-wif | unchanged |
| retire | fleet-playbook-curator | source package removed; deployed jobs untouched |
| keep | dev-diary | unchanged |
| keep | voice | inactive re-entry proposal only |
| keep | grill-me | unchanged |
| keep | tracer-bullets | unchanged |
| keep | semver-gate | retain PR146 absorption |
| keep | verify-before-claim | unchanged |
| keep | diagnosing-bugs | unchanged |
| keep | docs-hygiene | unchanged |
| keep | context-handoff | unchanged |
| keep | codebase-design | unchanged |
| keep | wayfinder | unchanged |
| keep | scope-fence | unchanged |
| keep | find-before-build | unchanged |
| keep | egress-gate | unchanged |
| keep | stop-rule | unchanged |
| keep | redgate | compatibility retained; simplification proposed |
| keep | recurrence-detector | unchanged |
| keep | jori | migration prerequisite remains open |
| keep | agent-compiler | proposed future absorber; no registry edit |
| keep | eval-ladder | unchanged |
| keep | consolidation-map | unchanged |
| keep | wave-research | retain PR149 absorption |

26 = 25 + 0 + 1; 25 = 25 + 0. Proposed future Jori absorption would be
25 = 24 kept + 1 merged-away + 0 retired, then 24 = 24 + 0 new. That absorption
has not occurred. PR150's proposed new package is outside today's before inventory.
No unratified disposition is counted as a completed retirement.

## Publication boundary found during this work

At the inspected main SHA, `.github/workflows/evals.yml:21-26` triggers on
pushes to main and PR opened/synchronize/reopened/labeled. Draft status is not
excluded. Feature branch push alone does not match the main-only push trigger.
However, opening a same-repository draft PR selects `grader-model` at lines
291-345 and `subject-model` at lines 347-385 without a `paid-evals` check.
The former posts `ping` to Anthropic Messages with `max_tokens:8`; the latter
runs `evals/paid/check-subject-model.sh`, which posts pings to OpenRouter Chat
Completions with the discovered packs' token reservation ceilings and retries.
No runtime secret availability or actual charge has been verified here.

The `paid-evals` label gates the large evaluation legs, not these two calls.
No supported no-spend option for a same-repository draft PR was found in these
jobs. Do not add a fork, skip marker, workflow edit or security-setting change
as an improvised bypass. Publication is pending authorization for the automatic
reachability calls (including provider reservation/retry semantics), or a
separately approved supported no-spend publication path. A dollar ceiling cannot
be promised from this source alone: the discovered model set, rates, provider
behavior and account limits were not measured. Main failure repairs, workflow
changes, paid runs, merge, release and installed activation remain outside scope.
