# `fixtures/native/replay/` — SYNTHETIC streams, in an invented vocabulary

Every `.jsonl` here was **hand-authored by this lane**. None of it was recorded
from `claude` or `codex`, and none of it is a claim about either CLI's real
stream shape. The real shape of `claude`'s stream is now recorded — see
`../streams/claude-2026-09-07.jsonl` and `../grammars/` — and these files were
deliberately **not** rewritten to match it. They are a vocabulary chosen to
exercise the state machine, and re-pointing them at real field names would blur
the one distinction this directory exists to keep sharp.

`synthetic-offline-form.grammar.json` is the matching grammar. It is loaded by a
helper inside `tests/test_adapters_and_protocols.py`, **not** by
`adapters.load_grammar()`, which reads only from `../grammars/` and only accepts
a document naming a capture that exists. Keeping the synthetic grammar off that
search path is deliberate: there must be no code path where a synthetic
vocabulary can be mistaken for a captured one.

Everything replayed from here runs as `AdapterClass.REPLAY` against a
`HostLedger(witness=CALLER_ASSERTED)`. `evidence_class_for` maps that to
`SIMULATED` with no branch to anything else, so these fixtures exercise the
session/turn/cancel/resume state machine without any of them being able to close
T26–T29, which stay `approval_gate: native-required` in the catalog and still
print `BLOCKED — approval required` with no token. The live forms that DID close
those cards on 2026-09-07 are separate tests, reachable only through
`run.py --id <TID> --approval-token <tok>`; their evidence is under
`../evidence/2026-09-07/`. Replaying that evidence is REPLAY evidence, exactly
like replaying these files.
