# Handoff: retry-policy follow-up

## References

Spec:
This spec describes in full detail the exact retry semantics required: exponential backoff starting at 200ms, a maximum of five attempts total, up to 50ms of jitter added to each attempt, and a full circuit-breaker cutover after three consecutive failures inside any rolling thirty second window.
