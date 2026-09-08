# `fixtures/native/streams/` — real captures, one file per CLI that was driven

A file here is a **transcript of a live, approval-gated run** of an installed
agent CLI. Nothing here is hand-authored, and nothing here is synthetic. The
grammars in `../grammars/` are written **from** these files, never the other way
round (implementation contract §10.2, §11.1).

## What is here

| file | CLI | captured | how |
|---|---|---|---|
| `claude-2026-09-07.jsonl` | Claude Code 2.1.263 (`/home/SCRUBBED-USER/.local/bin/claude`) | 2026-09-07 | `CliDriver.spawn` under approval token `user-approved-2026-09-07-native`, one turn, prompt "Reply with exactly the word OK and nothing else." |

11 records, which is the whole of that session's stream — the contract asks for
"the first ~20 records" and a one-turn session produced fewer than that.

**Scrubbing.** Three substitutions were applied and nothing else: the capture's
temporary workspace path → `/tmp/SCRUBBED-WORKSPACE`, `/home/<user>` →
`/home/SCRUBBED-USER`, and the messaging socket path → `/tmp/SCRUBBED-SOCKET`.
Session ids, message ids, request ids, model ids, token counts and costs are
**as recorded** — they are the evidence. No key, token or credential appears in
the stream at all; the capture was checked for the home path and the socket path
before it was committed.

## What is NOT here

`codex-*.jsonl`. `codex exec --json` has never been driven in this repository,
so `load_grammar("codex-exec-json")` still raises and
`fixtures/native/grammars/` holds no codex document. That refusal is the signal
that the UNKNOWN is still open for codex: a guessed grammar parses a real stream
into silence (every `session_ack` misses, `session_id` stays `None`, every usage
field reads `UNKNOWN`) and the run then looks like *a harness that reported
nothing* rather than *a driver that was wrong*.

`../replay/` holds **synthetic** streams in a vocabulary this lane invented for
the offline forms of T26–T29. They are labelled synthetic in their own README,
they are not a claim about any CLI, they are deliberately kept off
`load_grammar`'s search path, and the sessions that replay them are
`AdapterClass.REPLAY` writing to a `witness=CALLER_ASSERTED` ledger. Nothing
they produce can be promoted.

## Replaying a capture is REPLAY evidence

Reading `claude-2026-09-07.jsonl` back through `ReplaySession` produces
`EvidenceClass.SIMULATED`, exactly as replaying a synthetic stream does. The
capture is a record of a native run; it is not itself a native run, and no
amount of re-reading it makes it one. Only `CliDriver.spawn`, under an approval
token in the run `Manifest`, over a `HostLedger` constructed
`witness=HOST_OBSERVED`, produces `NATIVE_PROVEN`.
