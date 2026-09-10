# Rate limiter design

## Candidate 1
State: per-key timestamps in one instance.
Depth: hides window expiration and counting.
Locality: one module; callers only ask allow(key).
Seam: injected clock makes exact window boundaries testable.

## Candidate 2
State: caller-owned counters and reset times.
Depth: thin arithmetic helper.
Locality: each caller must preserve and expire counters.
Seam: shares arithmetic but exposes policy in every caller.

## Candidate 3
State: shared remote store.
Depth: hides atomic cross-process counters.
Locality: adapter plus network backend.
Seam: backend boundary permits a distributed limit later.

Chosen: Candidate 1 for the scoped in-process contract; retain the clock seam.
