---
description: Manually trigger a fleet-playbook curation pass (same PR-only, cited path as the daily cron).
argument-hint: "[path-to-diff.json]   (defaults to running detect first)"
---

Invoke the `fleet-playbook-curator` skill and follow `skills/fleet-playbook-curator/SKILL.md`
+ `PROMPT.md` to curate the playbook outside the daily schedule.

Same guarantees as the scheduled run — no shortcuts:

- Run the deterministic `detect` first (`list-fleet-members.sh` → `diff-fleet.sh`) so you
  curate against a real, cited diff, not guesswork.
- `gather-context.sh diff.json` for the changed members only.
- Edit the playbook with fully-cited `repo@sha:path` claims; append exactly one changelog entry.
- Land the result as a **PR**, never a direct push to `main`.

If nothing changed, stop — do not re-curate on no signal.
