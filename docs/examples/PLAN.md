# Example gallery — the plan

A verification surface: real, provenanced with-skill / without-skill model
pairs published to GitHub Pages next to the plugin docs, sourced from the
behavioral eval tier. Built as a Red Gate tracer; this is the roadmap to full
coverage. Each phase names its verifier (what proves it done).

## Where it stands

| Piece | State |
|---|---|
| `capture-example.sh` (results.json → snapshot) | shipped, unit-tested |
| `build-examples.sh` (snapshots → static `index.html`) | shipped, deterministic, cheap-tier `--check`; redesigned per `DESIGN.md` |
| `build-index.sh` (marketplace + snapshots + packs → landing `docs/index.html`) | shipped, deterministic, cheap-tier `--check` |
| role-by-role model disclosure + same-family refusal (capture script, cheap tier, page) | shipped |
| Sigstore attestation of CI-captured snapshots (`refresh-examples.yml`) | shipped; fires on the next refresh run |
| cheap tier §19 (sync + provenance guard) | shipped, mutation-proven |
| `pages.yml` (deploy from Actions, `enablement:true`) | shipped, runs on merge to main |
| behavioral CI captures each pack's snapshot | shipped (artifact) |
| biweekly review-gated refresh PR | shipped (`refresh-examples.yml`) |
| committed snapshots | **15 of 24** — every plugin without a pack (12) plus scope-fence, redgate and agent-compiler; subagent seeds, ungraded, each with an independently judged divergence. The live spread is computed on the gallery page from the data, never hand-counted here |

**Coverage today:** 12 plugins have a promptfoo pack and can auto-capture a
*graded* example (agent-compiler, find-before-build, fleet-playbook-curator,
graveyard, redgate, scope-fence, semver-gate, stop-rule, tailscale-wif,
verify-before-claim, voice, wayfinder). 12 have no pack, so they have no
eval-derived example yet (codebase-design, context-handoff, dev-diary,
diagnosing-bugs, docs-hygiene, egress-gate, grill-me, orchestrate,
plugin-factory, prove-the-undo, recurrence-detector, tracer-bullets). The
cheap tier checks the snapshot row above against the data directory and the
marketplace, so these counts cannot silently go stale.

## The gap that blocks everything else

Capture runs in CI and uploads the snapshot as an **artifact**; nothing writes
it back to the repo. So the gallery cannot populate itself — every card has to
be committed by hand. **Phase 2 closes this loop; it is the highest-leverage
next step and everything after it is cheap.**

## Phases

### Phase 1 — tracer *(done)*
One plugin end to end: capture script, generator, guard, Pages wiring, one
real seed. Verifier: cheap tier green, page renders, `--check` couples.

### Phase 2 — close the capture → commit loop *(done)*
A scheduled + `workflow_dispatch` **refresh-examples** workflow: run the
promptfoo packs (keys already in CI), run `capture-example.sh` per plugin,
and **open a PR** with the updated `docs/examples/data/*.json` + regenerated
`index.html`. A PR (not a direct push) keeps a human in the loop on what gets
published — the snapshots are real model output and deserve a glance.
- Shipped as `.github/workflows/refresh-examples.yml`: **biweekly** (1st & 15th,
  06:00 UTC) + `workflow_dispatch`, runs the packs, captures, regenerates, runs
  the cheap tier, and opens a **review-gated PR** (`peter-evans/create-pull-request`,
  branch `examples/refresh`, never a direct push). Merging publishes to Pages.
- Decisions settled by the owner: cadence **biweekly**, **review-gated** (not
  auto-merge).

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

### Phase 4 — the 13 unpacked plugins *(done: 13 of 13 seeded)*
Two honest options per plugin, decided per plugin:
- **Subagent seed** (like scope-fence now): a real, labelled-ungraded pair,
  available immediately, no pack required.
- **New promptfoo pack**: the durable answer — gives a graded example *and* a
  behavioral regression test the plugin currently lacks. More work.
- **Done — all 13 seeded** via real model runs (a 40-agent pass: per plugin a
  designer read the SKILL.md and built a discriminating scenario, two agents
  answered it with the skill and with a generic stub, and an independent
  reader judged the honest divergence). Each reader's verdict is published
  verbatim on its card, so a weak example is visible as weak rather than
  dressed up. At seeding the tagged verdicts were 1 stark, 7 moderate and
  2 subtle, with three seeds described in prose without a one-word grade;
  an earlier version of this line said "1 stark, 9 moderate, 2 subtle", which
  was a miscount. Two more seeds (redgate, agent-compiler) arrived with
  PR #80, one of them judged "strong" — the reader's word, kept as written.
  The current spread is computed on the gallery page.
- **The subtle ones are the useful signal**, not a failure: `docs-hygiene` and
  `codebase-design` are where a strong model already does most of what the
  skill asks unaided. Those are the two best candidates for a real promptfoo
  pack (a cheaper subject model will show the gap the seed cannot), and the
  two places to ask whether the skill is earning its context.
- A plugin with neither seed nor pack simply has no card — the gallery never
  fabricates one.

### Phase 5 — provenance you can check, models disclosed by role *(done)*
The question this phase answers: how does a reader know a pair is real model
output and not typed by hand — and which model did what?
- **Every model disclosed by role.** A snapshot's `provenance` now names the
  `subject_model` (answered both sides), the `grader_model` (the pack's
  pass/fail rubric, read from `promptfooconfig.yaml` by `capture-example.sh`,
  never hard-coded) and the `judge_model` (who wrote the divergence verdict),
  plus `same_family_judge`. The cheap tier refuses a snapshot missing any of
  them. The gallery shows them on every card and in a page-level table.
- **A model never grades its own family.** Every behavioral pack tests one
  model (`openrouter:nvidia/nemotron-3-ultra-550b-a55b`) and grades with another
  (`anthropic:messages:claude-sonnet-5`); the cheap tier now checks every pack
  for that, `capture-example.sh` refuses to write a same-family pair, and the
  gate rejects a graded snapshot whose subject and grader share a family. The
  15 seeds were all Claude on every side, and now say so out loud
  (`same_family_judge: true`, a warning badge on the card) instead of reading
  as independent verdicts. They are replaced, not re-dressed: the 12 packed
  plugins get a graded pair on the next refresh run.
- **A signed chain back to the run.** `refresh-examples.yml` passes the
  Actions `run_url` into each snapshot, keeps every `results.json` as a
  90-day artifact, and signs each snapshot it wrote with
  `actions/attest-build-provenance` (only the files that run produced — a seed
  or an unchanged snapshot never carries a run's signature). A reader runs
  `gh attestation verify docs/examples/data/<plugin>.json --repo
  JRichlen/agent-plugins --signer-workflow …/refresh-examples.yml`; the card
  prints that command, the file's SHA-256 and the run link. Seeds have no
  signature and the page says exactly what a seed can and cannot prove.
- **The page itself** was redesigned around the research in `DESIGN.md`:
  sidebar + filters, verdict first, prompt verbatim behind a one-line preview,
  transcripts clamped with one expand and stacking on narrow screens, a
  nutrition-label provenance block per card, and a "how to verify" section.
  The landing page is now generated (`docs/build-index.sh`) so it lists every
  plugin with its example / grading / deep-dive status.

### Phase 6 — polish
- **Staleness guard**: flag a snapshot older than the `SKILL.md` it demonstrates
  (its captured-at commit predates the skill's last change) — a `docs-hygiene`
  or cheap-tier check, so an example can't quietly misrepresent a changed skill.
- **Two-way linking**: each plugin `README`/`AGENTS.md` links to its gallery
  card. (The root `README`, the landing page and the cards already link.)
- **Multiple scenarios per plugin** where the extra pressure case adds signal
  (e.g. scope-fence pressures 1 and 2).
- **Per-plugin permalink pages**, if the single page grows past what the
  sidebar and filters can carry.
- **Re-seed the 12 unpacked plugins with a different judge family** — or,
  better, give them packs so the grade is a real rubric rather than a
  same-family reader.

## Invariant this feature keeps

Every published pair is a real, provenanced model run — captured from the eval
tier, never hand-written — with every model named by role, and no model
grading its own family. The gallery shows truth, including where a skill's
effect is modest (the seed card says so out loud) and where the verdict is not
independent (the same-family badge). No card without two real outputs and
role-by-role provenance; the cheap tier enforces it, and a CI-captured pair is
signed to the run that produced it.
