---
description: Stand up the daily fleet-playbook automation for an owner/glob (one-shot, confirm-gated).
argument-hint: <owner> <glob>   e.g. acme 'service-*'
---

Invoke the `fleet-playbook-curator` skill and follow `skills/fleet-playbook-curator/SKILL.md`,
specifically the **Deploy safely** section.

This is the ONE high-stakes action (it creates a repo, installs cron workflows, and needs
write credentials), so:

1. **Plan first.** Run `scripts/scaffold-repo.sh <fleet-name> <owner> <glob> <tmp-dir> --plan`
   and show the user exactly what would be written and where.
2. **Confirm.** The target is a NEW, distinct, default-private repo (suggest `<fleet>-playbook`)
   — never a `docs/` dir inside a fleet member. Get explicit confirmation before creating anything.
3. **Materialize.** Run the scaffolder without `--plan`, create the private repo, commit, and
   push. Set the `ANTHROPIC_API_KEY` secret and (optionally) the `FLEET_AGENT_CMD` variable on it.
4. **Verify.** Trigger the `Fleet sync` workflow once via `workflow_dispatch` and confirm the
   detector commits a facts manifest and (if anything changed) opens a curation PR.

Never run this unattended. Re-running is safe: the scaffolder is idempotent and never
overwrites curator-owned prose.
