---
name: fleet-playbook-curator
description: >-
  Deploy and operate daily GitHub automation that curates a living, self-invalidating
  operating index (a "fleet playbook") for a glob of repos — always pointing at the
  repos as the source of truth, never posing as it. Use when someone wants a
  cross-repo runbook/index that stays current on its own, asks to "curate a playbook
  for a fleet", to "monitor a set of repos and keep operating docs in sync", or to
  set up daily change-detection + agentic curation over an owner/glob of repositories.
---

# fleet-playbook-curator

## Invariant

The fleet-playbook is a curated INDEX that only says where truth lives and when it was read: every substantive claim carries a `repo@sha:path` citation and an "as-of" stamp, uncited claims are omitted or flagged stale rather than asserted, and the agent's interpretation reaches `main` only through a reviewed PR while the deterministic detector auto-commits only facts.

Everything below exists to keep that true. The single rule that makes it survive the
model being wrong, lazy, or prompt-injected: **facts auto-commit; interpretation is
PR-only.** A deterministic (no-LLM) detector writes trusted facts to `main`; the agent's
curation is quarantined to a pull request a human reviews.

## When to use this

- Someone has a **fleet** — a set of repos matched by an `owner/glob` (e.g.
  `acme/service-*`), likely growing — and wants a single place that
  explains how to operate across them without hand-maintaining it.
- They want that place to **stay current automatically** and to **never drift into a
  false source of truth**: it routes to the real repos/files/commits, timestamped.
- Two verbs:
  - **deploy** — stand up the automation once (`commands/deploy-fleet-playbook.md`).
  - **curate** — run/trigger a curation pass (`commands/curate-fleet-playbook.md`), or
    let the daily cron do it in the deployed repo.

This is a router/index, **not** a runbook. Runbooks assert authoritative procedure;
this only ever says "check X — as of `<sha>` it did Y."

## Mental model

Think cache, not document:

| Cache concept | This system |
|---|---|
| invalidation | the deterministic daily detector (no LLM) |
| cache-fill / re-index | the agentic curator (LLM), only when a real change is detected |
| entry discipline | never serve a claim without its source + as-of SHA |
| invalidation log | the human-readable `CHANGELOG.md` |

## How it works

### 1. The fleet primitive (deterministic, LLM-free)

A fleet is **data**: `owner`, a `glob`, and optional exclude rules (see
`templates/fleet.example.yaml`). Membership is **always re-derived live** from the glob
and joined on GitHub's stable **`node_id`**, never `full_name`, so a rename never looks
like a simultaneous remove+add.

- `scripts/list-fleet-members.sh <owner> <glob>` — enumerates members via
  `gh api orgs/<owner>/repos --paginate` (the correct, strongly-consistent rate bucket —
  **not** the Search API), filters by glob, emits a manifest keyed by `node_id` with each
  member's `head_sha` and `pushed_at`.
- `scripts/diff-fleet.sh <old-manifest> <new-manifest>` — a cheap cost cascade
  (membership add/remove/rename → `pushed_at` drift) that emits a boolean `changed` and a
  structured `diff.json`. **Membership changes are a first-class change type** — a
  new/renamed/archived/unreadable member matters more than content drift and is what most
  needs a changelog line.

### 2. The daily loop (in the deployed repo)

One scheduled workflow, two jobs (`templates/fleet-sync.yml`):

- **detect** — pure bash/`gh`/`jq`, **no LLM credential**. Stamps every member's
  `head_sha` every run (an independent staleness clock that keeps working even if the LLM
  step never runs), diffs against the committed manifest, and **auto-commits the facts
  manifest to `main`**. State lives in committed git history, never the Actions cache
  (which silently expires ~7 days).
- **curate** — `needs: detect`, `if: needs.detect.outputs.changed == 'true'`. The LLM
  credential is scoped to **this job only**. It reads **only the changed repos**, edits
  (never regenerates) the playbook, and **opens a PR — never pushes to `main`.**

### 3. What "good curation" is

Selection, not summarization (summaries go stale fastest). The rule:

> If it's greppable in one repo, it does **not** belong in the playbook. If it spans
> repos or is tribal knowledge, it does.

Entry points, cross-repo interactions, "which repo owns what", gotchas, invariants.

### 4. The writing rules (how the playbook talks)

- **Directives, not declaratives.** Not "the inventory lives in `hosts.yml`" but
  "**check** `hosts.yml` — as of `<sha>` it held the inventory."
- **Every substantive claim carries `repo@sha:path`** and an as-of stamp. An uncited
  claim is omitted or flagged `STALE`, never asserted. A citation is only valid if the
  surface it names was actually read this pass (present in `context.json`); a **removed
  member is never read, so it may carry only a manifest-level removal note, never a file
  citation.** If someone asks about a removed member's old README in a one-shot/no-tool
  setting, answer only with that manifest-level removal fact; do **not** speculate about
  its prior contents, show retrieval steps for it, or even include an example
  `repo@sha:path` citation for that removed member. `scripts/validate-citations.sh`
  enforces the structural half — it runs in the curate job before the PR opens and in the
  cheap eval — so **both** a removed-member file citation **and** a citation to a path that
  was never in the gathered tree are a red build, not a review catch. (This guard exists
  because the `ansible-homelab-sim` simulation caught a curator inventing content for a
  removed member, and the first live curation caught claims citing files whose contents
  were never gathered.) What it can't check deterministically — whether the cited file's
  *contents* actually support the claim — is the behavioral eval's and the human/verifier
  layer's job, not this gate's.
- **Freshness banner** at the top: last successful curation + "if older than N days,
  distrust this."
- Prefer embedding a **verification command** (a `grep`/`gh` one-liner) over stating a
  fact, so the reader re-derives truth from source.

The playbook's required shape is the contract in `templates/fleet-playbook/`
(`SKILL.md` banner + `source-of-truth: false` frontmatter + `index.schema.json` citation
ledger + `CHANGELOG.md`).

## Deploy safely

`deploy` is the one high-stakes action (it creates a repo, installs cron workflows, and
provisions write credentials). It is **human-invoked, never unattended**, runs a
**dry-run/plan first**, and asks for confirmation. The target is a **new, distinct,
default-private repo** (e.g. `<fleet>-playbook`) — never a `docs/` dir inside a fleet
member, so the playbook can never visually read as canonical. Scaffolding is idempotent
(`scripts/scaffold-repo.sh`): reruns are byte-identical and never clobber curator-owned
prose.

## Portability

The fleet scripts, `gather-context.sh`, `PROMPT.md`, the templates, and the eval checks
are portable `bash`/`gh`/`jq` with no Claude-Code-only dependency. The one harness-specific
seam is the curate workflow's agent invocation, exposed as a swappable `AGENT_CMD`
(default `claude -p` / the Claude Code Action). `agents/fleet-playbook-curator.md` is a
thin Claude-Code wrapper; on any other harness, read this SKILL.md and run the same steps.

## The design, recorded

The full architecture, the reconciled decomposition, the eval-tier mapping, and the risks
live in `docs/DESIGN.md` in this plugin.
