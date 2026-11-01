# Fleet playbook curator retirement

The repository package is retired: 26 installable plugins become 25. This removes
new-install catalog exposure, its commands/agent/templates/scripts and its active
per-plugin evaluation cells. It does not uninstall an installed copy or disable,
modify or delete any deployed playbook repository, workflow, schedule or credential.
Those systems require a separate inventory and explicit user direction.

This retirement narrows the optional product catalog; usage and deployment state
are not established by fixture results. It is not a claim that generic docs-hygiene,
recurrence-detector or agent-compiler replaces its scheduled cross-repository service.
Loss: this marketplace no longer offers new fleet discovery, daily detection,
agent curation or fleet-playbook deployment. Existing deployed repositories vendor
the runtime scripts and prompt, as shown in the former scaffold-repo.sh, and can
continue independently. Their current state was not inspected.

## Preserve the useful lessons

The full source, fixtures and design remain at
[the pre-retirement revision](https://github.com/JRichlen/agent-plugins/tree/0f0eb6f172e1e2d06396011a78e689f06ca48969/plugins/fleet-playbook-curator).

- An index points to truth; each substantive claim needs its own source revision,
  path and as-of stamp. A document-level freshness banner does not prove each claim.
- A structural citation validator can reject a removed/unread repository or an
  unread file surface; it cannot prove that the content supports the claim.
- Mutable repository names can be renamed or reused. The former validator checks
  provided node IDs without silently falling back to a reused name. This is not a
  guarantee that GitHub node IDs never change format.
- Detector liveness and prose curation are different clocks. Do not claim a fresh
  scan proves unmerged prose current. A no-change heartbeat distinguishes an idle
  fleet from a failed schedule. Separate branches protect unreviewed sibling edits.
- Typed ADD/UPDATE/REMOVE deltas and reused SHAPE tags remain supported through
  [dev-diary's existing reference](../../plugins/dev-diary/skills/dev-diary/references/consolidate-delta.md).
  Retain source citations on index deltas; recurrence-detector reads those logs.
  No duplicate delta skill or new scheduler is introduced.

## Restore, rehearsed before removal

Source revision: `0f0eb6f172e1e2d06396011a78e689f06ca48969`.
Before removal, all 45 tracked package files were restored into a scratch directory
using git cat-file; each restored file's Git blob SHA matched git ls-tree.
Literal result: `RESTORE PASS: 45 tracked files restored from 0f0eb6f172e1e2d06396011a78e689f06ca48969; every Git blob SHA matched.`
The first git-archive comparison failed on exported line endings; no removal occurred
until the exact-blob rehearsal passed.

Restore the package with:

```sh
git restore --source=0f0eb6f172e1e2d06396011a78e689f06ca48969 -- plugins/fleet-playbook-curator
```

Full rollback must also restore the isolated retirement diff's marketplace entry,
README, routing roster, active task/arm/red-team cells, testing inventory and caller
updates, then regenerate derived pages/configs and run free checks. Restoring only
the directory is incomplete: the reverse catalog lock rejects an unlisted package.
Once committed separately, revert that retirement commit; before commit, review and
reverse only its patch, preserving unrelated proposal work. No live system undo is
needed because this change performs no live-system mutation.

## Compatibility and evidence boundary

Current references in docs-hygiene now distinguish a historical example from an
available package; its source link is pinned above. Recurrence-detector reuses the
existing dev-diary delta reference. Historical design, research, timeline, paid-run
receipts and the frozen PR129 experiment remain untouched.

Removed active coverage is documented in docs/testing.md. It is not reported as a
passing fleet evaluation. No paid behavioral or real-worker evidence was collected;
local static checks cannot establish replacement parity or deployed-system status.
