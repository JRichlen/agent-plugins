# Example gallery — the plan

A verification surface: real, provenanced with-skill / without-skill model
pairs published to GitHub Pages next to the plugin docs, sourced from the
behavioral eval tier. Built as a Red Gate tracer; this is the roadmap to full
coverage. Each phase names its verifier (what proves it done).

## Where it stands

| Piece | State |
|---|---|
| `capture-example.sh` (results.json → snapshot) | shipped, unit-tested |
| `build-examples.sh` (snapshots → static `index.html`) | shipped, deterministic, cheap-tier `--check` |
| cheap tier §19 (sync + provenance guard) | shipped, mutation-proven |
| `pages.yml` (deploy from Actions, `enablement:true`) | shipped, runs on merge to main |
| behavioral CI captures each pack's snapshot | shipped — **uploads an artifact, does not commit it** |
| committed snapshots | **1 of 23** (`scope-fence`, subagent seed, ungraded) |

**Coverage today:** 10 plugins have a promptfoo pack and can auto-capture a
*graded* example (find-before-build, fleet-playbook-curator, graveyard,
scope-fence, semver-gate, stop-rule, tailscale-wif, verify-before-claim,
voice, wayfinder). 13 have no pack, so they have no eval-derived example yet
(codebase-design, context-handoff, dev-diary, diagnosing-bugs, docs-hygiene,
egress-gate, grill-me, orchestrate, plugin-factory, prove-the-undo,
recurrence-detector, redgate, tracer-bullets).

## The gap that blocks everything else

Capture runs in CI and uploads the snapshot as an **artifact**; nothing writes
it back to the repo. So the gallery cannot populate itself — every card has to
be committed by hand. **Phase 2 closes this loop; it is the highest-leverage
next step and everything after it is cheap.**

## Phases

### Phase 1 — tracer *(done)*
One plugin end to end: capture script, generator, guard, Pages wiring, one
real seed. Verifier: cheap tier green, page renders, `--check` couples.

### Phase 2 — close the capture → commit loop
A scheduled + `workflow_dispatch` **refresh-examples** workflow: run the
promptfoo packs (keys already in CI), run `capture-example.sh` per plugin,
and **open a PR** with the updated `docs/examples/data/*.json` + regenerated
`index.html`. A PR (not a direct push) keeps a human in the loop on what gets
published — the snapshots are real model output and deserve a glance.
- Verifier: a dispatch run opens a PR whose diff is only snapshot/HTML changes
  and whose cheap tier is green; merging it makes new cards appear on Pages.
- Decision needed: **cadence** (on every behavioral run? weekly? dispatch-only?)
  and **auto-merge vs review** (recommend: review — real transcripts, low volume).

### Phase 3 — widen to the 10 packed plugins *(graded, automatic)*
Once Phase 2 exists, coverage is a byproduct: each pack's next run captures a
graded pair. Replace the ungraded scope-fence seed with its graded capture.
- Verifier: ≥10 snapshots committed, each `graded: pass|fail` (not seed),
  cheap tier §19 green for all.
- Selection policy to settle: a pack has several scenarios — which becomes the
  published one? Recommend the scenario with the **starkest, graded divergence**
  (with-skill pass + negative-control behaving as the stub should), chosen
  deterministically by `capture-example.sh`, not by hand, so it can't be
  cherry-picked. Encode the rule; the cheap tier already refuses a snapshot
  without both outputs + provenance.

### Phase 4 — the 13 unpacked plugins
Two honest options per plugin, decided per plugin:
- **Subagent seed** (like scope-fence now): a real, labelled-ungraded pair,
  available immediately, no pack required.
- **New promptfoo pack**: the durable answer — gives a graded example *and* a
  behavioral regression test the plugin currently lacks. More work.
- Recommend: seed the few with obvious before/after value now (prove-the-undo,
  egress-gate, diagnosing-bugs) for an immediately fuller gallery; grow packs
  for the rest on the existing behavioral-pack backlog, and let Phase 2 fill
  them in as graded captures land. A plugin with neither simply has no card —
  the gallery never fabricates one.

### Phase 5 — polish
- **Staleness guard**: flag a snapshot older than the `SKILL.md` it demonstrates
  (its captured-at commit predates the skill's last change) — a `docs-hygiene`
  or cheap-tier check, so an example can't quietly misrepresent a changed skill.
- **Two-way linking**: each plugin `README`/`AGENTS.md` links to its gallery
  card; the root `README` links to the gallery. (Cards already link to docs.)
- **Multiple scenarios per plugin** where the extra pressure case adds signal
  (e.g. scope-fence pressures 1 and 2).
- **Landing/index niceties**: filter by graded/seed, per-plugin permalink pages.

## Invariant this feature keeps

Every published pair is a real, provenanced model run — captured from the eval
tier, never hand-written. The gallery shows truth, including where a skill's
effect is modest (the seed card says so out loud). No card without two real
outputs and provenance; the cheap tier enforces it.
