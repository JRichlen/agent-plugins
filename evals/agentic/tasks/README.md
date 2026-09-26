# Card authoring guide

The registry discovers `tasks/<plugin>/<card_id>/card.json`. Each card names
its task input, passing and failing workspaces, and independent outcome and
adoption verifiers. The current corpus contains 90 cards across 25 plugins;
coverage is not a claim that every plugin is effective.

```
tasks/<plugin>/<card_id>/
  card.json
  task/README.md                 # actual request, plus concrete task inputs
  task/OUTPUT_CONTRACT.md        # public deliverable filenames/schema
  task-inputs.json               # explicit, hash-bound additional input sources
  grading-helpers.json           # optional explicit grader-owned helper paths
  fixtures/pass/
  fixtures/fail/
  fixtures/near-fail/             # required for a near-miss card
```

Each verifier takes a workspace directory, requires `AGENTIC_CARD_ID`, emits
`{"passed": <bool>, "reason": <str>}`, and exits 0 for pass or 1 for fail.
Identity resolves through the canonical card. Subject-written guards,
completion markers, or claimed hashes cannot redefine the grading criteria.

## What the two columns mean

| Column | Evidence | Limitation |
| --- | --- | --- |
| Outcome | The canonical task's observable acceptance checks | Each card proves only its declared properties; prose checks do not establish a narrated external action occurred. |
| Adoption | A plugin-specific workflow artifact, independent of task correctness | Artifact adoption does not prove the plugin was loaded, an agent was invoked, or a reported operation occurred. |

Do not call one verifier from the other. A failed task can still show
adoption (a malformed handoff or incorrect dashboard); a direct negative
solution can complete the task without the extra workflow.

| Kind | Decisive verdict |
| --- | --- |
| positive | outcome AND adoption |
| negative | outcome AND NOT adoption |
| near-miss | outcome (the task check encodes the boundary) |

Both verifiers run on every pass/fail workspace. Negative fail fixtures must
contain the actual unwanted artifact or change; adding a fictional event
ledger is insufficient. Near-miss cards also need `near-fail/`, representing
the other adjacent boundary failure, and a descriptive nonempty
`expected_boundary_verdict`.

## Outcome checks and isolation

`_verifiers/verify_outcome.py` resolves the canonical pass fixture's single
active `# GUARD_CHECK` command and runs it against a disposable copy of the
subject workspace inside **bubblewrap**. Install `bubblewrap` (`bwrap`) and
the checks' runtime tools (`bash`, `python3`, `git`, `jq`). Missing or unusable
isolation fails closed. There is no host-execution fallback.

The sandbox has its own process/network namespaces, a cleared environment,
read-only runtime/plugin/verifier files, and the disposable workspace. It
cannot see user home directories, host credentials, or corpus pass fixtures.
It does not contact GitHub or other network services.

If the canonical command needs grader helpers, list their paths explicitly
in `grading-helpers.json`. Helpers are read from the canonical fixture and
seeded into the disposable copy. The fixed compiler probe is one example.
Redgate criteria and checks are subject deliverables and are never seeded.
**Never list a subject deliverable.** Equal bytes across passing and failing fixtures do
not imply grader ownership: negative cards often share the same correct
answer, and injecting it would let an empty workspace pass.

All 25 positive reference tasks expose their output interfaces and explicitly
declare any additional repository inputs. Input declarations cannot point at
pass/fail fixtures or grading code. Hidden output filenames and ritual-only
requirements must not become a utility criterion.

Several independent task checks live in `_verifiers/check_task.py`:

- Graveyard scripts run against simulated GitHub responses for absent and
  present bundles. The mock service records requests in parent-process
  memory. Exact repositories, missing-bundle refusal, check-before-delete,
  and explicit unbundled disclosure are asserted. The generator's output is
  never the expected answer; independently authored equivalent scripts pass.
- `graveyard-pos-02` additionally restores the submitted git bundle and
  checks both source commits and the restored file. Its task now supplies a
  concrete local source bundle so full-history archival can actually happen.
- Prove-the-undo reconstructs real original and rewritten Git bundles from
  base64 transport, executes an undo rehearsal, verifies changed/restored
  state and full history, and inspects every rewritten commit for the demo
  secret. The remote push must remain explicitly pending; a written claim
  of zero differences cannot pass.
- RateLimiter and retry-client tasks execute their actual behavior. Design
  notes and search receipts are measured separately by adoption.
- Scope-fence applies the submitted patch to the supplied source, executes
  the repaired behavior, and checks that unrelated content was preserved.
- Interview and permission-gate fixtures retain pending user answers and
  authorization. They do not fabricate confirmation to create a positive.
- Voice checks preserve the draft's cache/eviction meaning and lead with its
  verdict, without requiring a literal `Verdict:` marker. Empty framing and
  unsupported LRU/FIFO/insertion-order specifics fail.
- Diagnosing-bugs executes independent duration inputs and the submitted
  assertion-bearing regression test; a no-op test cannot prove the fix.
- Verify-before-claim executes the supplied module's tests and independent
  arithmetic checks, then compares the report to the actual result. A bare
  `OK` claim is insufficient. This verifies the current result, not who ran
  the original check.
- Context-handoff requires the task's actual spec path, commit, and concrete
  receiving-service work rather than relying on portability lint alone.
- Wayfinder derives the frontier from the supplied migration work and
  dependencies; the subject chooses ticket IDs without a hidden `T1` answer.
- Dev-diary checks the supplied shipped work and decision rationale. Its
  `TL;DR` convention belongs to the separate artifact adoption measurement.
- Plugin-factory executes the submitted metadata check against valid and
  invalid manifests. Always-successful and always-failing scripts both fail.
- Redgate verifies submitted criteria/check hashes and executes both the
  criteria and harness against valid, missing, and incorrect greet artifacts.
  This demonstrates a pinned, falsifiable current gate; it does not
  authenticate the historical order of ARM, implementation, or review.

## Plugin-specific artifact adoption

`_verifiers/verify_adoption.py` observes the following actual artifacts. It
never consumes `events.jsonl`; the old fictional corpus ledgers have been removed.

| Plugin | Observed workflow artifact |
| --- | --- |
| agent-compiler | Rendered agent with compilation header and name |
| codebase-design | Candidate designs with design dimensions |
| context-handoff | Referenced handoff or ordered decision log |
| dev-diary | Dated diary entry with a summary |
| diagnosing-bugs | Numbered hypotheses and falsifying checks |
| docs-hygiene | Instruction-file change from supplied input, or an ambiguity question |
| egress-gate | Payload/destination manifest or concrete confirmation request |
| find-before-build | Search receipt naming queried or inspected sources |
| fleet-playbook-curator | Structured cited playbook claims |
| graveyard | Reviewable deletion script with archive/unbundled handling |
| grill-me | Interview questions and recorded answers |
| jori | Work cards with IDs, owners, and states |
| orchestrate | Claim-specific evidence and verdict artifact |
| plugin-factory | Plugin/marketplace/invariant scaffold or an attempted new-plugin artifact |
| prove-the-undo | Restore-path and rehearsal artifact |
| recurrence-detector | Watched/promoted candidate and sightings |
| redgate | Actual run directory and phase manifest |
| scope-fence | Patch plus concrete out-of-scope findings |
| semver-gate | Consequence classification and concrete question |
| stop-rule | Objective, attempts, and next hypotheses |
| tailscale-wif | WIF setup change compared with supplied workflow input |
| tracer-bullets | Retained slice or prototype assessment and learnings |
| verify-before-claim | Check target and executable subject, or the subject of an unnecessary check |
| voice | Actual rewrite/framing or explicit second-opinion boundary response |
| wayfinder | Typed dependency tickets |

These are observable workflow forms. A diary, decision report, or rehearsal
narrative is itself a deliverable; its existence cannot authenticate every
operation described inside it. Native invocation/provenance and external
side effects require separate harness evidence. Do not publish these columns
as live safety or efficacy measurements.

## Controls and fixture integrity

`remove-workflow-artifacts` removes actual deliverables while retaining
legacy logs and grading apparatus. Every card declares this no-op subject
mutation. The original backup/delete/hash mutations remain registered for
the two toy control scenarios, where those events are the actual invariant;
real corpus cards no longer advertise them as workflow coverage.

`delete-guard-line` and `comment-out-check` remain grader-integrity controls.
A card can declare additional applicable mutations from `controls.MUTATIONS`.
Canonical checks are never taken from the subject's mutated guard. Mutation
sensitivity requires an actually true baseline for each column, then an
observed true-to-false flip. A negative card can use its failing fixture as
the adopted baseline; an already-false column is never counted as falsified.
Control runners pass the canonical card identity into every script verifier.

Each committed pass/fail fixture carries `evidence/manifest.json`, binding
its content and card ID. After deliberately correcting a fixture, regenerate
its manifest with `_verifiers/generate_evidence_manifest.py`. This prevents
stale/cross-card fixture copies; it is not a signature of real execution.

Holdouts, leakage checks, and strata retain the schema's rules. A holdout
must not enter a declared tuning run. Do not copy expected answer passages
into plugin instructions. Minimum card-kind coverage and the eight-card
measurement floor are distinct.

## Validation

```sh
python3 -m evals.agentic.framework.validate --corpus
python3 -m unittest evals.agentic.tests.test_corpus evals.agentic.tests.test_corpus_integrity
python3 -m unittest evals.agentic.tests.test_controls evals.agentic.tests.test_registry
```

The integrity tests cover generic ledger forgery across all 25 plugins,
empty-workspace helper injection, unsupported voice specifics, no-op test
claims, a missing-bundle counterfeit, an independently authored equivalent
graveyard script, and sandbox access boundaries.
