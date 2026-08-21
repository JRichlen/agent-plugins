# fixture: single current claim (negative control)

This is a fixture snippet, not real prose read by the skill. It stands in
for a single instruction file asserting a script lives at
`skills/plugin-foo/scripts/deploy.sh` — a path that DOES exist in
`repo-tree/`. This is a negative control: it proves check-path-claim.sh
distinguishes CURRENT from STALE rather than always reporting one or the
other regardless of input.
