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

Everything below exists to keep that true.

<!-- MEASURED: asked to design this automation cold, with "I'm the only
     maintainer, nobody reviews anything" as explicit pressure, the unaided
     model produced the facts/interpretation split unprompted and defended
     it under that exact pressure — facts to main, prose to a labeled PR,
     no auto-merge. That routing decision is already base-model default; it
     doesn't need more SKILL.md prose to hold. What the same probe did NOT
     produce is per-claim citation discipline (see "The writing rules"
     below) — that's where this plugin earns its slot. -->

**Facts auto-commit; interpretation is PR-only.** A deterministic (no-LLM) detector
writes trusted facts to `main`; the agent's curation is quarantined to a pull request a
human reviews.

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

<!-- MEASURED: the same cold-design probe that got the facts/interpretation
     split right (see Invariant, above) produced only DOCUMENT-level
     provenance when left to its own judgment — "a header naming the model,
     the run, and the manifest sha" at the top of the file. It never
     produced PER-CLAIM citation, never produced `repo@sha:path` on the
     individual claim, and never produced "uncited claims are omitted or
     flagged STALE" as a rule. This is the gap that's actually load-bearing:
     document-level provenance tells a reader the file was generated
     responsibly; it says nothing about whether any ONE sentence in it is
     still true. The rules below exist because that distinction does not
     show up unprompted. -->

**Citation is per-claim, not per-document.** A trustworthy-looking header at the top of
the file ("generated by Claude on 2026-08-23 from manifest sha abc123") is not a
substitute for this — it tells a reader the *file* was produced responsibly, not that
any individual *sentence* in it is still true. Every sentence stands or falls on its own
citation:

- **Directives, not declaratives.** Not "the inventory lives in `hosts.yml`" but
  "**check** `hosts.yml` — as of `<sha>` it held the inventory."
- **Every substantive claim carries `repo@sha:path`** and an as-of stamp, attached to
  that claim, not inherited from a document-level banner. An uncited claim is **omitted
  or flagged `STALE`, never asserted** — silence or an explicit stale-marker are the only
  two acceptable outcomes for a claim you can't cite; "probably still true" is not a
  third option. A citation is only valid if the surface it names was actually read this
  pass (present in `context.json`); a **removed member is never read, so it may carry
  only a manifest-level removal note, never a file citation.** If someone asks about a
  removed member's old README in a one-shot/no-tool setting, answer only with that
  manifest-level removal fact; do **not** speculate about its prior contents, show
  retrieval steps for it, or even include an example `repo@sha:path` citation for that
  removed member. `scripts/validate-citations.sh` enforces the structural half — it runs
  in the curate job **before** the PR opens and in the cheap eval — so **both** a
  removed-member file citation **and** a citation to a path that was never in the
  gathered tree are a red build, not a review catch. (This guard exists because the
  `ansible-homelab-sim` simulation caught a curator inventing content for a removed
  member, and the first live curation caught claims citing files whose contents were
  never gathered.) What it can't check deterministically — whether the cited file's
  *contents* actually support the claim — is the behavioral eval's and the
  human/verifier layer's job, not this gate's.
- **Freshness banner** at the top is additive, never a replacement for per-claim
  citation: last successful curation + "if older than N days, distrust this." It tells
  the reader when the *file* was last touched; it does not tell them which claims in it
  were re-verified that day versus untouched since curation began. Per-claim `as-of`
  stamps carry that distinction — the banner alone can't.
- Prefer embedding a **verification command** (a `grep`/`gh` one-liner) over stating a
  fact, so the reader re-derives truth from source.

The playbook's required shape is the contract in `templates/fleet-playbook/`
(`SKILL.md` banner + `source-of-truth: false` frontmatter + `index.schema.json` citation
ledger + `CHANGELOG.md`).

### 5. Three mechanics a future maintainer will want to simplify away — don't

<!-- MEASURED: the same cold-design probe argued against all three of these,
     articulately, unprompted — one clock is simpler than two, a heartbeat
     line is noise on a fleet that never changes, one reusable branch avoids
     branch sprawl. Each argument is locally reasonable and each one is
     wrong for a reason that isn't visible from inside a single design
     session — it only shows up once you've watched the pipeline run for
     weeks, or once an adversarial simulation exercises the failure path.
     Undocumented, the next agent to touch this plugin will make the exact
     same locally-reasonable argument and "clean this up." Read the
     rationale below — and `docs/DESIGN.md` / `templates/fleet-sync.yml`'s
     own inline comments, which is where each of these was first worked
     out — before removing any of the three. -->

- **Two clocks, not one: `LAST_VERIFIED` is separate from "last curated."** `detect`
  stamps `fleet-playbook/LAST_VERIFIED` every single run, whether or not anything
  changed; the CHANGELOG's newest *curation* entry is a different, sparser clock that
  only advances when a real change was found. Collapsing these into one "freshness"
  timestamp is the obvious simplification, and it's wrong in both directions at once: a
  fleet that legitimately hasn't changed in 45 days would show a 45-day-old stamp,
  telling readers to distrust a playbook that was in fact re-verified again this
  morning; meanwhile a playbook rotting behind an unmerged curate PR would show today's
  date and look fresh, because the detector kept running even though the *prose* stopped
  advancing. Two clocks, two truths — one says "the fleet was scanned," the other says
  "the prose was updated." A reader needs both, and needs them not conflated.
- **A no-change run still writes a heartbeat line to `CHANGELOG.md`.** When `detect`
  finds nothing different, it appends `- <timestamp> no change; fleet re-verified`
  instead of writing nothing. This looks like pure noise on a quiet fleet — and that's
  exactly the argument for cutting it, and exactly why it's wrong. The CHANGELOG is the
  *only* artifact a human skims to judge whether the pipeline is alive at all. Without
  the heartbeat, "nothing changed today" and "the cron silently broke three weeks ago"
  produce an **identical** CHANGELOG — a gap with no new lines either way. With it, a gap
  in the dated heartbeats is itself the alarm: the newest entry being old is direct
  evidence the daily loop stopped, not just evidence the fleet has been quiet. Silence
  must never be ambiguous between "verified, unchanged" and "never ran" — that ambiguity
  is the exact failure shape this plugin exists to prevent everywhere else, so it can't
  be allowed to reappear here in its own liveness signal.
- **Curation opens a fresh, timestamped branch every run (`curate/<UTC timestamp>`) —
  never one reusable branch.** Reusing a single `curate` branch reads as tidier: fewer
  branches, one place to look. It breaks the moment two things are simultaneously true
  elsewhere in this design — both by construction: the backpressure check (see "The
  daily loop") *expects* curation PRs to sometimes sit open and unmerged for a while,
  and treats that as a normal, monitored state, not an error. If a second run reused
  that same branch while the first PR was still open for review, landing its edits would
  require force-pushing over the first run's diff — silently discarding an unreviewed
  curation nobody had looked at yet. That's the "green build, no signal, work quietly
  destroyed" failure class this plugin's own workflow comments call out and guard
  against elsewhere (the no-op changelog line above is the same principle applied to a
  different silent-discard path). A fresh branch per run means every curation attempt is
  independently reviewable, independently mergeable or closeable, and never at risk of
  clobbering a sibling run's unreviewed work.

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
