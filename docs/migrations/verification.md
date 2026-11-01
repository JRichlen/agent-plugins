# Verification ownership migration

The former Redgate product and its universal round driver are retired.
Verification is one service in `verify-before-claim`: direct claim checks and,
only when selected, executable acceptance via `verify-work`.

## What disappears

- Default activation for all nontrivial work; the broad driver and its
  calibration, recursion, round-type and handoff-envelope reference files.
- Repeated scope/approval/risk/question rules, plan/scout/retro cadence,
  model/budget governance and a separate mandatory round ledger.
- A separate public package, install recommendation and coordinator identity.

Core owns shared intent, authority, task state and interaction. Existing task
methods own their procedures; semver-gate, scope-fence, egress-gate and stop-rule
retain their responsibilities. Verification returns evidence to that owner.

## What survives, and why

Existing `.redgate/` records demonstrate demand for resuming pinned criteria,
checkers and evidence. The small scaffold/index/reconcile helpers and contract
write guard move under `plugins/verify-before-claim/`. Hash drift rejection,
fresh evidence and fault-versus-unmet distinctions remain. They do not prove
independent reviewer identity; the caller must establish and record it.

No new task must use that legacy storage format merely because it is complex.
The labels ARM/TRACE/MIDDLE in old manifests are a data ABI, not a renewed
universal workflow. New cases no longer create budget/cadence fields or a
mandatory gates.log. The index reads historical ledgers when they exist.

## Explicit compatibility

Old source paths for `scaffold-run.sh`, `criteria-index.sh` and `reconcile.sh`
remain thin `exec` adapters. There is no old manifest or full duplicate skill.
Use the same relative paths under `plugins/verify-before-claim/` for new calls.
Installed old packages and commit-pinned dependencies are not silently edited.
New explicit command: select `verify-work` from the installed verification
package. Old names are migration/history only, not current products.

Before source removal, all 24 tracked old-package files were restored from
`2ff596caf3be9fd59ebfe42d17b05ccab1f1da1d` into a workspace scratch directory;
every Git blob hash matched. Restore the isolated migration as a unit if needed:
package contents alone are insufficient without catalog, routes and coverage.
No commit, release, global installation or live hook activation happened here.

Free executable controls exercise red checks, unpinned/re-pin refusal, changed
criteria/checkers, missing fresh evidence, protected writes, harness faults,
empty verdicts and nonzero exits. Historical model findings remain historical;
no new model-based efficacy or cross-host qualification is claimed.
