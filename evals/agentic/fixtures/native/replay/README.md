# `fixtures/native/replay/` — SYNTHETIC streams, in an invented vocabulary

Every `.jsonl` here was **hand-authored by this lane**. None of it was recorded
from `claude` or `codex`, and none of it is a claim about either CLI's real
stream shape — that shape is an open UNKNOWN, documented in `../streams/README.md`.

`synthetic-offline-form.grammar.json` is the matching grammar. It is loaded by a
helper inside `tests/test_adapters_and_protocols.py`, **not** by
`adapters.load_grammar()`, which raises for exactly the reason the streams
README gives. Keeping the synthetic grammar out of `load_grammar`'s search path
is deliberate: there must be no code path where a synthetic vocabulary can be
mistaken for a captured one.

Everything replayed from here runs as `AdapterClass.REPLAY` against a
`HostLedger(witness=CALLER_ASSERTED)`. `evidence_class_for` maps that to
`SIMULATED` with no branch to anything else, so these fixtures exercise the
session/turn/cancel/resume state machine without any of them being able to close
T26–T29, which stay `approval_gate: native-required`.
