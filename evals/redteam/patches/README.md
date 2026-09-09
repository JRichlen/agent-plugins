# Winston logger lifecycle backports

The pinned Promptfoo 0.122.0 uses Winston 3.19.0 and winston-transport 4.9.0.
Its logger can end file
transports while records remain in the logger's readable buffer. A real
288-row offline evaluation completed, then crashed during shutdown. A separate
logger-only reproduction consistently lost 35 of 128 records and exited 1.

`winston-3.19.0-drain.patch` is the exact logger lifecycle hunk from
[Winston PR 2599](https://github.com/winstonjs/winston/pull/2599), head
`569d0ba4f5774415daf1541153db0ff16f1bb7ad`. That upstream PR was **open and
unmerged** when reviewed on 2026-09-09. Its event-driven fix waits for the
readable buffer to drain before ending transports, then waits for their
existing finish events. It keeps logging enabled and does not catch or ignore
write failures. The upstream MIT license is retained in `LICENSE.winston`.

The stronger two-file regression then exposed a second lifecycle defect:
`winston-transport` completed a batch before its individual asynchronous log
writes completed. With the first fix alone, close returned successfully but
the debug file contained only 2 of 16 error records. This was record loss,
with no configured file size limit, rotation or rate filter involved.

`winston-transport-4.9.0-batch.patch` adapts the callback accounting fix from
[transport issue 49](https://github.com/winstonjs/winston-transport/issues/49)
and [PR 50](https://github.com/winstonjs/winston-transport/pull/50), head
`3fe62b8daa15280c35f3373d7a5e7688351f3954`, also open and unmerged at review.
It waits for every accepted log callback before completing the batch. The
adaptation also completes an entirely filtered batch, propagates callback or
format errors, and lets Writable invoke each individual write callback. It
does not copy the old proposal's missing empty-batch completion or duplicate
individual-callback calls. Its MIT license is in `LICENSE.winston-transport`.

After installing the existing pinned tool versions into a controlled tool
directory, provision both backports explicitly:

```bash
python3 evals/redteam/bin/provision-logger.py --promptfoo-home "$PROMPTFOO_HOME" --apply
python3 evals/redteam/bin/provision-logger.py --promptfoo-home "$PROMPTFOO_HOME" --check
```

The two manifests record exact original, patched, and patch SHA256 digests. The
provisioner rejects unknown package versions or source bytes. It writes a
separate candidates and verifies both complete postimages before replacement.
`--check` never mutates an installation. Normal evaluation wrappers use that
read-only check; users must explicitly provision their controlled tool copy.
Promptfoo's version and distribution pin remain unchanged.

`evals.agentic.tests.test_redteam_logger` uses the installed Promptfoo logger
and actual file transports. It requires every byte of all 128 large debug
records and 16 error records to reach the correct files before close, checks
empty and filtered-batch shutdown, and keeps real write errors fatal. The existing offline
288-row integration remains a separate required test. A future dependency
upgrade must review this backport and update the pin deliberately.
