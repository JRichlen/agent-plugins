# tailscale-wif

Set up and troubleshoot **secretless** GitHub Actions -> Tailscale authentication
via Workload Identity Federation (WIF). Each run mints a GitHub OIDC token that a
Tailscale **Trust Credential** exchanges for a short-lived API token or ephemeral
auth key — so no Tailscale API key or OAuth client secret is ever stored. The
only things you keep are the **public** `oauth-client-id` and `audience`, in repo
variables.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install tailscale-wif@jrichlen
```

## What's in the box

- **Skill** — `skills/tailscale-wif/SKILL.md`: the two use cases (ACL GitOps and
  node join), the workflow requirements, the Trust Credential console fields, the
  OIDC subject-hardening gotcha, the decode-the-sub debug step, and the symptom ->
  cause table.
- **Agent** — `agents/tailscale-wif-setup.md` (Claude Code): computes the
  ID-embedded subject, walks you through the admin console, wires the repo
  variables, and edits the workflow. On other harnesses, follow the skill.
- **Command** — `/tailscale-wif` (`commands/tailscale-wif.md`).
- **Templates** — ready-to-copy workflows under
  `skills/tailscale-wif/templates/` for ACL GitOps, node join, and OIDC-sub
  debugging.
- **Script** — `skills/tailscale-wif/scripts/compute-subject.sh OWNER/REPO`
  prints the exact ID-embedded subject to paste into the console.

## The invariant

WIF auth is secretless: only the public `oauth-client-id` and `audience` are
stored (as repo variables, never secrets), the job always carries
`permissions: id-token: write`, and exactly one auth mode is passed. No
long-lived Tailscale credential is ever stored to enable a run.

## Cross-harness

Everything is plain GitHub Actions YAML plus `gh`/`curl`/`jq`. The command and
agent are Claude Code conveniences; the procedure ports to any harness via the
skill and scripts.

## License

MIT
