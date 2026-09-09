# Deliverable interface

Implement `rate_limiter.py` with `RateLimiter(limit, window_seconds, clock)` and `allow(key="default") -> bool`. The injected clock returns monotonic seconds. Allow up to limit requests per key per window; deny further requests until the window expires. Keys must be independent. A design-workflow artifact, when used, belongs in `docs/design-notes.md`; task utility is judged by executable limiter behavior, independently of that artifact.
