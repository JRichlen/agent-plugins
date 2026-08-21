# Handoff: retry-policy migration (violates the pointer-only rule)

## Live thread

Mid-implementation of the new retry policy for the ingest worker.

## References

Spec:
This spec describes in great detail the exact retry semantics that the
ingest worker must implement, including exponential backoff starting at
200ms, a maximum of five attempts total, up to 50ms of jitter added to each
attempt, and a full circuit-breaker cutover after three consecutive
failures inside any rolling thirty second window.

## Suggested skills

- context-handoff
