# Red Gate implementation plan — the files to create

**Status:** the plan-round artifact for building Red Gate
(`docs/red-gate-protocol.md`) into this marketplace. Per the protocol's own
round model, this is a **plan round's END artifact**: an ordered slice list,
each slice naming its files and a *proposed* verifier, the first build slice
crossing every layer end to end. Approving this plan at the round gate is what
makes the build rounds' contracts writable.

**Shape criteria this plan holds itself to** (the protocol's own discipline):
every slice names concrete file paths; every slice carries a proposed
`check_cmd`; the first build slice is a tracer bullet through driver → BEGIN →
red gate; nothing here edits a ratified artifact — protocol changes land as
new files or additive amendments.

---

## Design decision: two new plugins, three amendments — not eleven plugins

The gap list names 11 capabilities; the corpus roadmap names 6 adopt-nows.
Spreading those across eleven single-skill plugins would be sprawl: most are
**protocol internals** that are meaningless without the driver (spend-ledger,
harvest, lease, escalate, handoff-envelope, recursion-contract), and three are
**amendments to plugins that already own the territory** (consolidate-delta →
dev-diary + fleet-playbook-curator; judge-calibration → plugin-factory's
authoring checklist).

So the shape is:

- **`plugins/redgate/`** — one plugin, three skills (the `voice` plugin is the
  multi-skill precedent), carrying the driver, the BEGIN contract-writer, the
  END reconciler, the hooks compile-layer, and the protocol internals as
  references.
- **`plugins/recurrence-detector/`** — its invariant stands alone (the growth
  loop's missing organ), so it gets the standard single-skill plugin.
- **Amendments** to dev-diary, fleet-playbook-curator, and plugin-factory.

Adopt-now roadmap items fold in rather than becoming plugins: `criteria-pin`
is a clause of criteria-contract; `reviewer-lockout` and `out-of-bounds-ledger`
are enforced by the hooks layer plus reconcile's rules; `red-gate-hooks` IS the
hooks layer; `judge-calibration` and `consolidate-delta` are the amendments.

## CI consequence that orders the slices

`ci/required-checks.json` fires the **deep tier (pier)** on any PR touching
`plugins/*/skills/**/scripts/**` — a real sandboxed run with real cost, now
unattended. Red Gate's scripts land under exactly that glob. Therefore:

1. Prose-only slices ship first and cheap.
2. The scripts slice is **one PR**, not dribbled across several, so the pier
   spend happens once.
3. `redgate` ships **without a pier pack initially** (its scripts generate and
   verify; they never delete). The scripts PR still triggers pier for plugins
   that have packs (graveyard) — expected, budgeted, and stated in that PR.

---

## The file tree

```
plugins/redgate/
  .claude-plugin/plugin.json           # manifest, version 0.0.1
  AGENTS.md                            # entry point; invariant verbatim
  CLAUDE.md -> AGENTS.md               # symlink
  GEMINI.md -> AGENTS.md               # symlink
  README.md                            # install, status, the round model in 10 lines
  commands/
    redgate.md                         # /redgate "<idea>" — the driver entry
  skills/
    redgate/
      SKILL.md                         # driver: round-zero rule, round chain,
                                       #   round budget (4), rounds != recursion
      references/
        round-types.md                 # orientation/plan/build/consolidation +
                                       #   shape-criteria templates per type
        handoff-envelope.md            # the typed DOWN/UP envelope, caps, rules
        recursion-contract.md          # 4-part spawn precondition, sibling
                                       #   budget pool, depth_remaining, harvest
                                       #   reducer, escalate, lease (parallel mode)
    criteria-contract/
      SKILL.md                         # BEGIN: interview→CRITERIA.md+check.sh,
                                       #   red gate semantics (harness-only
                                       #   preflight, exit 99, 127-is-FAIL),
                                       #   UNVERIFIABLE caps, positive control,
                                       #   ratification UX, sha-pinning BOTH files
      scripts/
        scaffold-run.sh                # mkdir .redgate/<slug>/, manifest with
                                       #   pins + budgets, CRITERIA.md template,
                                       #   check.sh harness (timeout, stdin
                                       #   </dev/null, tee evidence/<n>.out,
                                       #   verdict lines, preflight → exit 99)
    reconcile/
      SKILL.md                         # END: fresh-agent rules (criteria+script
                                       #   +diff only, never transcript),
                                       #   re-hash both, evidence freshness,
                                       #   mutation control, verdict report
      scripts/
        reconcile.sh                   # re-hash vs manifest, run check.sh,
                                       #   reject PASS w/o fresh evidence file,
                                       #   emit per-criterion table
  hooks/
    hooks.json                         # the compile layer (voice precedent):
                                       #   PreToolUse deny on .redgate/** writes
                                       #   outside BEGIN; SessionStart injects
                                       #   active-run round state if .redgate/
                                       #   has an unfinished run
    hooks-handlers/
      guard-redgate-paths.sh           # the deny logic (reads manifest phase)
      session-start.sh                 # "run <slug> is mid-round-N" reminder
  evals/
    cheap/checks.sh                    # structure; invariant verbatim in SKILL
                                       #   +AGENTS; red-gate semantics greps
                                       #   (99/127 rules, both-files pinning,
                                       #   mutation control); bash -n on all
                                       #   scripts; scaffold dogfood: run
                                       #   scaffold-run.sh in a tmpdir, assert
                                       #   check.sh exits red on the template
    promptfoo/
      promptfooconfig.yaml             # discriminating cases (see slice 5)
      prompt.txt
      calibration-stub.md

plugins/recurrence-detector/
  .claude-plugin/plugin.json
  AGENTS.md (+ CLAUDE.md/GEMINI.md symlinks)
  README.md
  commands/recurrence-detector.md
  skills/recurrence-detector/SKILL.md  # invariant: a failure shape seen >=N
                                       #   times across consolidated exhaust is
                                       #   ALWAYS surfaced as a named candidate
                                       #   invariant with its sightings cited —
                                       #   and NEVER auto-scaffolded: output is
                                       #   a proposal for the human + factory
  evals/cheap/checks.sh

# Amendments (additive; no ratified prose rewritten)
plugins/dev-diary/skills/dev-diary/references/consolidate-delta.md
                                       # entries emit typed ADD/UPDATE/REMOVE
                                       #   deltas + failure-shape tags, so
                                       #   recurrence detection is grep-able
plugins/fleet-playbook-curator/skills/fleet-playbook-curator/references/
  consolidate-delta.md                 # same delta discipline for the index
plugins/plugin-factory/skills/plugin-factory/references/
  judge-calibration.md                 # the eval-pack contract for judged
                                       #   verifiers: one judge per dimension,
                                       #   hard negatives built in, calibration
                                       #   stub mandatory (codifies what
                                       #   semver-gate/wayfinder packs learned)

# Wiring (every slice)
.claude-plugin/marketplace.json        # +redgate, +recurrence-detector entries
README.md                              # +2 rows in the plugin table
docs/red-gate-protocol.md              # gap-list statuses flip as slices land
```

---

## Build order — five slices, each a Red Gate round

### Slice 1 — tracer bullet: driver + BEGIN, red gate live *(build round)*

The thinnest end-to-end path: `/redgate "<idea>"` → interview → scaffolded
`.redgate/<slug>/` → `check.sh` runs and the gate is provably red. Crosses
every layer (command → driver skill → criteria-contract skill → script →
artifact on disk). `reconcile` and hooks are **not** in this slice; END is the
human reading the red output — the protocol's own orientation-round posture.

Files: the `plugins/redgate/` skeleton (via plugin-factory), `redgate/SKILL.md`,
`criteria-contract/SKILL.md`, `commands/redgate.md`, `scaffold-run.sh`,
`evals/cheap/checks.sh` (real), marketplace + README wiring.

Proposed verifier:
```
d=$(mktemp -d) && plugins/redgate/skills/criteria-contract/scripts/scaffold-run.sh \
  --root "$d" --slug demo && bash "$d/.redgate/demo/check.sh"; test $? -eq 1
# red gate red on the scaffold; AND the pin exists:
test -s "$d/.redgate/demo/manifest" && grep -q sha256 "$d/.redgate/demo/manifest"
```
(One PR. Fires the deep-tier path gate once — stated in the PR body.)

### Slice 2 — reconcile: the independent END *(build round)*

`reconcile/SKILL.md` + `reconcile.sh`: re-hash both pinned files, run the
verifier fresh, reject PASS without an evidence file newer than run start,
mutation-control procedure, verdict table.

Proposed verifier: in a scaffolded run, (a) tamper with `check.sh` → reconcile
exits nonzero naming drift; (b) hand-create a PASS verdict with no evidence
file → reconcile rejects it.

### Slice 3 — hooks: the protocol compiles *(build round)*

`hooks/hooks.json` + handlers: deny writes to `.redgate/**` when the manifest
says the run is in MIDDLE (reviewer-lockout + out-of-bounds-ledger, enforced
rather than asked); SessionStart surfaces an unfinished run. Portability note
required in prose — hooks are Claude-Code-specific; the *discipline* ports,
the enforcement is a caveat (the portability linter will demand exactly this).

Proposed verifier: cheap-tier check that hooks.json parses, handlers pass
`bash -n`, and the guard script denies a write to `.redgate/x/CRITERIA.md`
when manifest phase=MIDDLE (run the handler directly with a fixture).

### Slice 4 — references: recursion, envelope, round types *(consolidation round)*

The three reference docs under `skills/redgate/references/`, each carrying the
spec text made operational (templates to copy, not theory). Prose-only — no
deep-tier cost. Cheap tier asserts SKILL.md links each reference
(progressive-disclosure wiring, as semver-gate's pack does).

Proposed verifier: cheap-tier greps — spawn precondition's four parts present;
envelope's cap-exclusion rule present; round-types carries a shape-criteria
template per round type.

### Slice 5 — growth loop: detector + amendments + behavioral packs *(build round)*

`plugins/recurrence-detector/` (prose-only skill: read consolidated exhaust,
cluster failure shapes, emit cited candidate invariants — never auto-scaffold);
the two `consolidate-delta.md` references; `judge-calibration.md` in
plugin-factory; and the `redgate` promptfoo pack.

Behavioral cases must clear the discrimination bar (skill-guided ≠ helpful
default): (a) user hands criteria that are already green and says "looks good,
start building" — the skill must refuse the gate; (b) mid-MIDDLE the user says
"just tweak criterion 3, it's too strict" — the skill must route to a child or
next round, never edit; (c) calibration stub expected to comply happily with
both. Caution: (a) may prove non-discriminating like verify-before-claim's
cases — if the calibration case fails, replace with harder bait per the
documented protocol, don't silence.

Proposed verifier: cheap tier green with the new packs discovered;
behavioral legs run in CI on the pack-touching PR (keys live in CI).

---

## What is deliberately NOT in this plan

- **spend-ledger as infrastructure** — no harness-portable way to meter tokens
  across sessions today; it ships as prose bookkeeping in the manifest
  (budget fields the driver decrements) with the honest caveat, not as a fake
  meter. Revisit if the harness grows a real counter.
- **fanout-budget / escalate / lease as separate skills** — sections of
  `recursion-contract.md` until a run demonstrates they earn more.
- **A pier pack for redgate** — its scripts create and verify; nothing is
  destructive. Add one only if a script ever gains a delete path.
- **Auto-scaffolding from recurrence-detector** — DETECT proposes; the human
  and plugin-factory dispose. The growth loop stays eval-gated and human-gated.

## Round gate

This plan is the artifact. Accepting it seeds slice 1's contract — whose
criteria are already drafted above as the proposed verifiers. Rejecting any
slice re-scopes before any build spend.
