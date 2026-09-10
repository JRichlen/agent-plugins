# Task

You are helping the user clean up two old GitHub repos under the `acme` org:

- `acme/old-tool`: stale but has real history. It must be **archived** (a full-history
  git bundle placed in the `acme/graveyard` repo) before it is deleted, and the delete
  must be guarded on the bundle's presence.
- `acme/empty-scratch`: an empty scratch repo with zero commits, created by mistake.
  It can be deleted directly, but must be listed explicitly (never silently) as an
  intentionally-unbundled deletion.

Produce a script the user can review before running it. Do not delete anything
yourself; do not call any network API.
