# semver-gate

Classify a candidate action as PATCH/MINOR/MAJOR (semver-style blast-radius test) before acting, and rehearse the rollback of any irreversible one — name the restore path and exercise it. Act silently on PATCH, flag-and-stage MINOR, stop for explicit human sign-off on MAJOR; sign-off authorizes the action, the rehearsal proves the exit. Use mid-task when unsure how much autonomy to take: which path to pick, overwriting unreviewed state, disabling a safety toggle, deletes, drops, force-pushes, migrations, or any judgment call settings.json's autoMode patterns don't enumerate.

## Why "semver-gate"

The working title going in was `semver-autonomy`. `semver-gate` won out after
weighing it against the alternatives that came up during design:

- **`blast-radius-gate`** is truer to the exact phrase in the system prompt's
  "Executing actions with care" section, but it drops the semver identity
  entirely — and the semver borrow is the entire point: PATCH/MINOR/MAJOR are
  vocabulary an engineer already has memorized cold, which is what makes this
  a fast lookup instead of a fresh vibe-check every time.
- **`change-tier`**, **`escalation-semver`**, and **`decision-semver`** get
  the right ingredients in the name but read as noun-soup out of context,
  unlike the kebab two-word shape every other plugin in this marketplace uses
  (`dev-diary`, `plugin-factory`, `tailscale-wif`).
- **`semver-autonomy`** (the working title) names the *property* being
  measured (how much autonomy to take) rather than the *mechanism* doing the
  measuring.

`semver-gate` is the only candidate that does both required jobs in one
compound without strain: "semver" is the load-bearing borrow, and "gate"
names the mechanism — a checkpoint an action clears silently, clears loudly,
or doesn't clear without a human — which is exactly the right noun for
something that sits mid-task and decides whether to let an action through.
It doesn't collide with any existing plugin name in this marketplace
(`dev-diary`, `graveyard`, `tailscale-wif`, `plugin-factory`, `voice`,
`orchestrate`, `fleet-playbook-curator`, `grill-me`), and it reuses a word
("gate") this repo's own eval tiers already use for precisely this concept —
a checkpoint that must go green, not a rubber stamp — so the name plugs into
vocabulary this repo already speaks instead of introducing a fifth synonym
for the same idea.

## How it relates to what already governs agent behavior here

semver-gate is a judgment aid, not a new policy layer, and it never overrides
either of these:

1. **The system prompt's "Executing actions with care" section** — the
   reversibility + blast-radius principle that already governs every action.
   semver-gate operationalizes that principle into a checklist with a
   memorized vocabulary; it adds no new criteria.
2. **settings.json's `autoMode` block** (`hard_deny`/`soft_deny`/`allow`
   pattern matches, like the `pnpm db:push:*` and protected-branch rules) —
   a coded rule there always wins, full stop. semver-gate exists only for the
   much larger space a pattern list can't enumerate.

See `skills/semver-gate/SKILL.md` for the full classification test and
`skills/semver-gate/references/rubric.md` for the literal decision table.

## The second skill: prove-the-undo

`prove-the-undo` fires at the same moment as `semver-gate` — any action
`semver-gate` classifies as MAJOR, plus any delete, drop, force-push, schema
migration or teardown whose undo is not a cheap retry — so the two ship as
sequential steps of one flow rather than as separate installs:

1. **`semver-gate`** classifies the action and, on MAJOR, stops for explicit
   sign-off on the specific mechanism ("may I do this?").
2. **`prove-the-undo`** names the specific restore path, exercises it in this
   session (scratch restore and diff, the artifact's own verifier, or a dry
   run), and attaches the literal output next to the go/no-go decision ("if it
   is wrong, can I actually get back?").

Sign-off authorizes the action; the rehearsal proves the exit. Neither
substitutes for the other, and an irreversible MAJOR action proceeds only
after both. `skills/prove-the-undo/SKILL.md` carries the rehearsal and
`commands/prove-the-undo.md` is its entry point. Both skill and command keep the
name `prove-the-undo`, so anything that refers to the skill by name keeps
resolving.

`prove-the-undo` was previously a separate plugin (`prove-the-undo@jrichlen`,
v0.0.1). Installing `semver-gate@jrichlen` v1.1.0 or later now includes it; if
you have the old plugin installed, uninstall it so the skill is not registered
twice.

No behavioral (promptfoo) pack ships for `prove-the-undo`, deliberately: its
invariant (caution before irreversible actions) sits squarely inside
base-model safety training, the exact non-discriminating shape documented
six-for-six in verify-before-claim's pack header — a calibration stub would
pass unaided and the pack would measure the model, not the skill. Add one
only with a scenario argued in writing to genuinely diverge from the
naturally-helpful/naturally-cautious default. Its invariant is defended by the
deterministic checks in `evals/cheap/checks.sh`.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install semver-gate@jrichlen
```

## License

MIT
