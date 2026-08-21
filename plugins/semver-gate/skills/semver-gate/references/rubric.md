# semver-gate — decision rubric

This is the literal, greppable decision table the SKILL.md points to. Evaluate
top-to-bottom per candidate action, apply the tie-break, then look up the
behavior. Keep this table's wording stable — the cheap eval asserts against
exact entries here, not a paraphrase.

## Decision table

| Property | PATCH | MINOR | MAJOR |
|---|---|---|---|
| Reversibility | Fully reversible, no residue (retry/re-run/checkout) | Reversible, but leaves a visible trace (added file, sent message, new capability) | Not reversible, or reversible only via a costly/risky counter-action (restore from backup, renegotiate access, re-request trust) |
| Blast radius / visibility | Local to agent's own working state only; nobody else observes it | Visible to the user/team, but stays within the current task's owned scope | Crosses into shared, production, or other-people's state; visible to or affecting parties beyond the requester |
| Contract change | Touches no interface/schema/protection-rule/promise anyone else relies on | Adds to a contract (new endpoint, new field, new file) without breaking what exists | Removes, overrides, or redefines a contract someone else depends on (schema break, disabling a protection, redefining what "protected" or "prod" means) |
| Cost to undo | ~0 (retry, git checkout) | Low-to-moderate (revert commit, delete the addition, send a correction) | High or unbounded (data loss, leaked credential, broken trust, an open window while a guardrail is down) |

## Tie-break rule

Any single property landing in **MAJOR** makes the whole action **MAJOR**,
regardless of the other three columns. This mirrors Conventional Commits: a
`BREAKING CHANGE` footer overrides the type that carries it, no matter how
small the diff looks. An action that is additive on three properties and
destructive on the fourth is MAJOR, not "mostly MINOR."

## Behavior lookup

| Tier | Act? | Disclosure | Alternative-naming | Staging |
|---|---|---|---|---|
| PATCH | Act silently | Mention once, folded into the ordinary summary | Never | No gate, no staged step |
| MINOR | Act now | Flag prominently, at the moment it happens — not buried in a final summary | Name the real alternative only if one genuinely exists; offer to switch | Stage as its own discrete next step, not folded into the PATCH-level work |
| MAJOR | Stop before acting | Ask via structured question, naming the specific mechanism, not the general goal | If re-asked after a prior "yes" to something adjacent, ask again specifically for the mechanism | Blocks further related work in this thread until resolved; if a structural block fires after sign-off, surface it and offer the least-destructive alternative, then wait again |

## Worked classifications

Use these as calibration anchors when an edge case is ambiguous.

| Candidate action | Reversibility | Blast radius | Contract change | Cost to undo | Tier |
|---|---|---|---|---|---|
| Fix a typo in a code comment | Fully reversible | Local only | None | ~0 | **PATCH** |
| Re-run a failed test | Fully reversible | Local only | None | ~0 | **PATCH** |
| Add a new optional field to a schema | Reversible, leaves a trace | Visible to team, in-scope | Additive, non-breaking | Low (revert commit) | **MINOR** |
| Write a new file proposing an approach | Reversible, leaves a trace | Visible to user | Additive | Low (delete file) | **MINOR** |
| Disable a branch-protection setting (`enforce_admins`) | Reversible only via re-enabling + trust repair | Shared repo state, visible to team | Overrides an existing protection contract | High (window of reduced safety, trust cost) | **MAJOR** |
| Force-push over a shared branch | Not reversible without coordination | Shared, affects teammates | Redefines branch history others rely on | High/unbounded | **MAJOR** |
| Run `pnpm db:push` bypassing the migration workflow | Reversible only via manual schema repair | Shared database state | Breaks the generate/migrate/journal contract | High | **MAJOR** |
| Apply a migration against a prod-gated runner | Not reversible without a restore | Production, affects all users | Redefines what "prod" currently looks like | High/unbounded | **MAJOR** |
| Recursive delete of a directory with unreviewed content | Not reversible without a backup | Depends on scope — local trash vs. shared storage | Can destroy state others depend on | High if no backup exists | **MAJOR** (unless proven local + backed up, then MINOR at most) |

## How this relates to what already exists

- **System prompt — "Executing actions with care":** the reversibility and
  blast-radius axes above are that section's own two axes, spelled out as a
  checklist. This table adds no third axis of its own; "contract change" and
  "cost to undo" are the same section's implicit sub-questions made explicit.
- **settings.json `autoMode`:** a coded `hard_deny` / `soft_deny` / `allow`
  pattern match (e.g. `Bash(pnpm db:push:*)`, protected-branch pushes, the
  "routine under this repo's prefix" allowlist) always wins over this table.
  This table is for the space no pattern enumerates.
