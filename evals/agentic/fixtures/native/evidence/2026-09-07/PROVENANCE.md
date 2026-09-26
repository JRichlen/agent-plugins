# Approved native run — 2026-09-07

Everything in this directory was produced by **live** invocations of the
installed Claude Code CLI on this host, driven through
`adapters.CliDriver.spawn` under approval token
`user-approved-2026-09-07-native`, over `HostLedger`s constructed
`witness=HOST_OBSERVED`. This is the first — and so far only — run in this
repository for which `evidence_class_for` legitimately returns
`NATIVE_PROVEN`.

## What was live

| file | catalog ID | what actually ran | CLI invocations |
|---|---|---|---|
| `t26-ledger.jsonl` | T26 | one fresh session, then a second turn by `--resume <acked id>`; both turns acknowledged on the CLI's own stream | 2 |
| `t27-ledger.jsonl` | T27 | fresh session A; a resume of A; a `--fork-session` fork of A; a second fresh session B in the **same** workspace, with a probe turn | 4 |
| `t28-ledger.jsonl` | T28 | a fresh session cancelled **mid-turn**: SIGTERM then SIGKILL on the process **group**, survivors witnessed before the reap, unread output tagged `LATE_OUTPUT` | 1 (killed) |
| `t29-ledger.jsonl`, `t29-attempt.json` | T29 | one fresh session; the ledger verified in-process with its own run-key capability; `attempt_from_session` produced the `NATIVE_PROVEN` attempt in `t29-attempt.json`, which `assert_native_backed` accepts against that ledger and refuses against a keyless reader | 1 |

Ten model-driven CLI invocations in total across the day, including one
exploratory capture (`../../streams/claude-2026-09-07.jsonl`) and one aborted
first attempt at T26.

`cli-version.txt` records the binary and version that produced all of it:
Claude Code **2.1.263**. `*-run-manifest.json` is the `contract.Manifest` each
run was executed under; its `approvals` tuple is what `CliDriver.spawn` checked
the token against.

## Replaying any of this is REPLAY evidence, never NATIVE_PROVEN

Reading these ledgers, or `../../streams/claude-2026-09-07.jsonl`, back through
any offline path produces `EvidenceClass.SIMULATED`, and that is not a policy —
it is the only thing the code can do:

* `ReplaySession` **refuses** a `witness=HOST_OBSERVED` ledger outright, so a
  replay's entries are always `caller-asserted`;
* `evidence_class_for(REPLAY, chain)` has no branch that returns
  `NATIVE_PROVEN`, and takes no argument that could add one;
* a `LedgerReader` in any later process has no run-key capability, so
  `is_verified()` is `False` and its reason is
  `unverifiable in this process (no run key)`. **These files cannot be
  re-blessed after the fact.** The HMAC key was minted with
  `secrets.token_bytes(32)` inside the run process and discarded with it; it is
  in none of these files, and `LedgerReader` refuses raw key bytes precisely so
  that nobody can supply a replacement.

This is asserted, not merely stated:
`CaptureReplayStaysSimulated.test_replaying_the_real_capture_is_simulated_and_cannot_be_host_witnessed`
replays `../../streams/claude-2026-09-07.jsonl` through `ReplaySession`, shows
that it *does* parse (real session id, real turn ack, real token counts) and
that the resulting attempt is `SIMULATED` with `session_id=None` and no
`event_ids` — the observed id recorded in `notes`, where it is visible and
weightless. Its sibling shows `ReplaySession` refusing a host-observed ledger
outright, which is the only route by which such a replay could have been
promoted.

So: the ledgers here are *tamper-evident records that a native run happened*.
They are not a native run, and re-running the framework over them does not make
one. Any future report that quotes these files must say **REPLAY of a
2026-09-07 native run**, never "native-proven".

## Why the ledgers are not scrubbed

Each `*-ledger.jsonl` is byte-exact as written. Editing one — even to replace a
path — recomputes nothing and simply breaks the hash chain, at which point
`verify_chain()` names the edited index and the file stops being evidence of
anything. The only host detail they contain is the absolute path of the CLI
binary (`/home/jrichlen/.local/bin/claude`); they contain no credential, no API
key, no run key, and no workspace content. (The *stream capture* under
`../../streams/` is a different artifact with no chain over it, and it **is**
scrubbed — see its README.)

The approval token id appears in the `APPROVAL_GRANTED` payloads and in each
manifest's `approvals`. That is deliberate: §10.6 requires the grant to be
recorded against the action it authorised, by **id**. The id is not a secret and
is not a credential — it authorises nothing on its own, because `spawn` also
requires the ledger, the manifest and the flag conformance check to hold.

## How to reproduce (this costs real model calls)

    python3 evals/agentic/run.py --id T26 --approval-token <your token>
    python3 evals/agentic/run.py --id T27 --approval-token <your token>
    python3 evals/agentic/run.py --id T28 --approval-token <your token>
    python3 evals/agentic/run.py --id T29 --approval-token <your token>

Without `--approval-token` those four IDs print
`BLOCKED — approval required (native-required)` and the offline `__offline_form`
siblings are what `--catalog` runs. Re-running the live forms **overwrites this
directory**.
