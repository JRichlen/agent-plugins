# fixture: single stale claim (never left in place)

This is a fixture snippet, not real prose read by the skill. It stands in
for a single instruction file asserting a script lives at
`plugins/ghost-plugin/scripts/run.sh` — a path that does not exist anywhere
in `repo-tree/`. Used to assert the invariant's "never left in place" half:
a stale claim must be detected, never silently accepted as current.
