# `fixtures/native/workers/` — real `python3` subprocesses, never a harness

These scripts are spawned for real by the offline form of T28 (cancellation) via
`protocols.WorkerPool`. They are genuine processes: they hold a process group,
they can ignore `SIGTERM`, they can emit output after a cancel has been issued.

They are **not** an agent harness. Contract §10.5 draws the line at "did a
model-driven agent harness run", not "did a process run", so evidence from these
is `REAL_FIXTURE` at best — `adapters.worker_evidence_class` has no branch that
reaches `NATIVE_PROVEN`, and `attach_session` refuses both
`AdapterClass.NATIVE` and a `witness=HOST_OBSERVED` ledger.
