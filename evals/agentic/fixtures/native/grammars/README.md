# `fixtures/native/grammars/` — grammars DERIVED FROM captures

One document per CLI whose stream has actually been recorded. `load_grammar`
loads only from this directory, and only when the document names a
`captured_from` file that exists in `../streams/`. Delete the capture and the
grammar stops loading — the binding is checked
(`test_a_grammar_whose_capture_is_missing_is_refused`), not merely declared.

## `claude-stream-json.json`

Every dotted path was read off `../streams/claude-2026-09-07.jsonl`:

| grammar slot | observed shape |
|---|---|
| `session_ack` | `{"type": "system", "subtype": "init", …, "session_id": "<uuid>"}` |
| `turn_ack` | `{"type": "assistant", "message": {…}, "session_id": "<uuid>"}` |
| `usage` | `{"type": "result", "usage": {…}, "duration_ms": …, "total_cost_usd": …}` |
| `result_text_field` | `result` on the terminal `type: result` record |

Three things the hand-authored usage fixtures flagged as unpinned, now answered
by the capture rather than by assumption:

1. **The stream-json envelope does nest usage** — under a top-level `usage`
   object on the `result` record (and, per-message, under `message.usage` on
   `assistant` records). The grammar reads the terminal one.
2. **Reasoning tokens are reported**, as
   `usage.output_tokens_details.thinking_tokens` (`0` in the capture — a
   *reported* zero, which `parse_usage` keeps distinct from absent).
3. **Wall clock and cost both come from the CLI**, as top-level `duration_ms`
   and `total_cost_usd` on the `result` record — not from the caller's own
   clock.

**`total_tokens` is deliberately unmapped.** The CLI reports no total anywhere
in the capture, so the grammar has no path for it and `parse_usage` returns
`UNKNOWN`. Summing the components here and calling the result "reported" is
precisely the reconstruction §10.4 bans.

## No `codex-exec-json.json`

`codex exec --json` has not been captured. `load_grammar("codex-exec-json")`
raises, and it must keep raising until an approved capture of that CLI exists.
