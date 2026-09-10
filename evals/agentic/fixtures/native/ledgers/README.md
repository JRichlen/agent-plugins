# `fixtures/native/ledgers/`

`genuine-caller-asserted.jsonl` is an intact, hash-chained ledger:
`LedgerReader.verify_chain().ok` is `True`, it names no bad index, and every one
of its eight entries is `caller-asserted`.

**There is deliberately no genuine host-observed ledger here.** A host-observed
entry's `host_signature.value` is an HMAC over a 32-byte run-scoped key, and §5.3
says that key is "held in memory, and never written into the workspace, the
manifest, or the ledger". A committed host-observed fixture would have to be one
of two things, and both are wrong:

* committed *with* its key — which is the forgery this lane exists to make
  impossible: anyone reading the repo could mint blessed entries;
* committed *without* its key — in which case `is_verified()` is `False` and it
  proves nothing a caller-asserted ledger does not already prove.

Host-observed ledgers are therefore built at test time, in a `tempfile.mkdtemp()`
directory, by a `HostLedger(witness=HOST_OBSERVED)` that mints its own key with
`secrets.token_bytes(32)` and refuses a supplied one.

`../tamper/` holds the four tamper classes of §5.2 plus a fifth, and
`../tamper/make_tamper_fixtures.py` regenerates every file here.
