# Handoff: retry-policy migration

## Live thread

Mid-implementation of the new retry policy for the ingest worker. The
exponential-backoff helper is written and unit-tested; next step is wiring
it into the queue consumer and updating the integration test that currently
asserts the old fixed-delay behavior.

## References

- Spec: docs/specs/retry-policy.md#section-3 — see "Backoff parameters"
- Issue: https://github.com/JRichlen/agent-plugins/issues/42
- Commit: 1a2b3c4 — introduced the new RetryPolicy type
- Diff: https://github.com/JRichlen/agent-plugins/pull/58/files

Plan:
The full rollout plan has several stages worth summarizing here since the
receiving session will want the shape without a separate lookup: land the
backoff helper, wire it into the consumer, then flip the feature flag
region by region. The authoritative version of this plan, including the
region rollout order and rollback triggers, lives at
docs/plans/retry-rollout.md — that block is over the four-line threshold on
its own, so it only stays compliant because this paragraph carries a real
path pointer to the live source rather than standing on prose length alone.

## Suggested skills

- context-handoff (load on arrival to re-run the boundary check)
- semver-gate (the queue-consumer change touches a shared contract)
