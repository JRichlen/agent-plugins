# semver-gate

Classify a candidate action as PATCH/MINOR/MAJOR (semver-style blast-radius test) before acting — act silently on PATCH, flag-and-stage MINOR, stop for explicit human sign-off on MAJOR. Use whenever you're mid-task and unsure how much autonomy to take on the next action: which of several implementation paths to pick, whether to overwrite unreviewed state, whether to disable a safety toggle, or any judgment call settings.json's autoMode patterns don't enumerate.

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

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install semver-gate@jrichlen
```

## License

MIT
