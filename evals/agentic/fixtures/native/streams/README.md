# `fixtures/native/streams/` — deliberately empty of stream captures

There is **no** `*.jsonl` capture and **no** `*.grammar.json` in this directory,
and `adapters.load_grammar()` raises rather than returning a grammar. That is the
designed state, not an unfinished one (implementation contract §10.2, §11.1;
backlog T30 "Depends on an UNKNOWN, and says so").

## Why nothing is here

The exact JSON field names emitted by

```
claude --print --output-format stream-json
codex exec --json
```

are **not established**. No transcript of either exists anywhere in this
repository (`find . -iname '*.jsonl'` and stream-json greps return nothing), and
producing one drives a real model — the approval-gated action of §10.6.

## Why a guess would be worse than nothing

A guessed grammar is not "approximately right". It is silently, totally wrong in
a way that is indistinguishable from a well-behaved harness that happened to
report nothing:

* every `session_ack` match misses, so `HarnessSession.session_id` stays `None`;
* an attempt with `session_id is None` can never be `NATIVE_PROVEN` (§10.2),
  so the run quietly downgrades to `SIMULATED` with no error;
* every usage field parses as `UNKNOWN`, which reads as "the CLI does not report
  tokens" rather than "the driver is looking in the wrong place".

The single signal that tells those two stories apart is the **absence of this
file**. `load_grammar` raising is that signal made loud.

## What removes this

One approved capture per CLI on a trivial prompt, committed here as
`{claude,codex}-<date>.jsonl` (first ~20 records is enough), with the grammar
written **from** the capture — never the other way round. The capture itself is
an approval-gated native run.

## What is NOT here

`../replay/` holds **synthetic** streams in a vocabulary this lane invented for
the offline forms of T26–T29. They are labelled synthetic in their own README,
they are not a claim about either CLI, and the sessions that replay them are
`AdapterClass.REPLAY` writing to a `witness=CALLER_ASSERTED` ledger, so nothing
they produce can be promoted.
