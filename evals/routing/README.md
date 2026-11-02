# Route methods and check decisions

This pack grades typed routing/next-action tuples with deterministic assertions.
It does not need an LLM judge. Changing the judge model cannot resolve ambiguity
in a fixture or disagreement between its prompt and expected tuple.

From the repository root, with Node installed:

```sh
node evals/routing/route-contract.test.js
node evals/routing/trajectory/step-contract.test.js
```

These free controls check grammar, closed vocabulary, guard composition,
permission boundaries and agreement between case oracles and the tuple contract.
They do not run a router or establish that models obey the instructions.

## Keep the distinctions meaningful

- S1 independently requires diagnosis, explicit acceptance and claim evidence;
  it now states the required criteria agreement directly. Omitting the claim
  guard remains a failure.
- S2 asks for a design walkthrough, not a pending blocking human decision.
  Its owner slot is `none`; nontrivial work still does not acquire an envelope.
- S4 retains the original archive-verification/sign-off request. Ordinary
  specialist checks and approval risk alone do not select a formal acceptance
  service. This boundary still needs live evidence; its oracle is unchanged.
- T1 names the missing selected-contract artifacts and owner agreement.
  Establishing criteria is not permission to implement.
- T2 identifies the proposed network-service action being judged. Continuing
  a different, already accepted local correction cannot answer that question.
- The direct README correction uses PATCH/auto, matching the prompt's taxonomy.
  `approved` remains the MAJOR explicit-answer vocabulary, not a general synonym
  for a routine requested task.

Fixture clarification creates a new experiment version. Preserve prior outputs
and failures; do not rescore them as if they answered the revised input, lower
thresholds, silently change repetitions or claim the model was repaired by free
source tests. Token-cap, transport, parse, oracle and behavior failures are
different observations. PR129's frozen corpus is separate and untouched.

Live execution requires the existing cost/disclosure gates. For future model
comparisons, read the [planning policy](../experiments/README.md) first.
