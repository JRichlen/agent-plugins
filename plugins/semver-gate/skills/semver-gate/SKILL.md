---
name: semver-gate
description: >-
  Classifies the AUTONOMY an agent should take for a pending action — act
  silently, act-and-flag, or stop-and-ask — by borrowing semver's precise
  MAJOR/MINOR/PATCH taxonomy and applying it to the action's blast radius
  instead of to a package's public API. PATCH (reversible, no observable
  contract change) means act, mention it in the summary, no gate. MINOR
  (additive, visible, non-breaking) means act, but flag it prominently and
  name the alternative if there's real ambiguity about which additive path is
  right — no blocking question required. MAJOR (irreversible, destroys or
  overwrites state, changes what's visible to others, or breaks a contract
  someone else depends on) means STOP: do not proceed on an assumption, get
  explicit human sign-off for that specific action first. Use this WHENEVER
  you are about to take an action and are unsure how much permission-seeking
  it warrants — before a schema push or migration, disabling a safety gate or
  branch protection, force-pushing, overwriting a file whose ownership is
  unclear, deleting or renaming something visible to others, or any other call
  about act-vs-flag-vs-ask. This does not replace an existing
  reversibility/blast-radius instruction or an autoMode permission classifier
  already in play — a hardcoded rule there always wins — it gives the
  judgment those leave implicit a precise, borrowed vocabulary and a concrete
  three-way mapping instead of a fuzzy reversible/risky binary.
license: MIT
---

# semver-gate

## The invariant

A MAJOR-class action — irreversible, destroys or overwrites state, changes
what's visible to others, or breaks a contract someone else depends on — is
**never taken on an assumption**. It always gets an explicit stop and an
explicit human answer to *that specific action* before proceeding — even
under time pressure, even after an adjacent "yes," and even when a block on it
could technically be routed around. PATCH-class actions never block. Where
classes collide — an action is simultaneously additive and destructive — MAJOR
always dominates, exactly as it does in the real spec.

Everything below exists to make that judgment call precisely, instead of by
feel.

## Why borrow semver specifically

Semantic Versioning already solved a version of this exact problem: *classify
a change by its actual consequence for someone who depends on you, then let
that classification drive an automated consequence.* It has done so, in
public, across the entire package ecosystem, for over a decade. The three
definitions are precise enough to quote and use as-is — from
[semver.org](https://semver.org)'s Summary and core rules:

> Given a version number MAJOR.MINOR.PATCH, increment the:
> 1. MAJOR version when you make incompatible API changes
> 2. MINOR version when you add functionality in a backward compatible manner
> 3. PATCH version when you make backward compatible bug fixes

And the normative rules behind those three words:

> Patch version Z (x.y.Z | x > 0) MUST be incremented if only backward
> compatible bug fixes are introduced.
> A bug fix is defined as an internal change that fixes incorrect behavior.

> Minor version Y (x.Y.z | x > 0) MUST be incremented if new, backward
> compatible functionality is introduced to the public API.

> Major version X (X.y.z | X > 0) MUST be incremented if any backward incompatible changes are introduced to the public API.

Read literally for agent actions instead of package APIs: **PATCH** is an
internal change that fixes something, invisible to anyone downstream.
**MINOR** adds something new without taking anything away from anyone who
already depended on the old shape. **MAJOR** is the only one of the three that
can hurt someone who was depending on the old contract — which is exactly why
it is the only one of the three that gets a hard stop below.

### The nearest existing precedent: Conventional Commits

[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) is the
closest thing that already exists to "classify an action by its type, and let
that classification drive an automated consequence" — the same shape this
skill applies to live actions instead of commit messages. Its own spec states
the mapping directly:

> `fix:` a commit of the type `fix` patches a bug in your codebase (this correlates with `PATCH` in Semantic Versioning).
>
> `feat:` a commit of the type `feat` introduces a new feature to the codebase (this correlates with `MINOR` in Semantic Versioning).
>
> `BREAKING CHANGE:` a commit that has a footer `BREAKING CHANGE:`, or appends
> a `!` after the type/scope, introduces a breaking API change (correlating with `MAJOR` in Semantic Versioning).
> A BREAKING CHANGE can be part of commits of any type.

And from its FAQ, stated even more bluntly as an automated consequence:

> `fix` type commits should be translated to `PATCH` releases. `feat` type
> commits should be translated to `MINOR` releases. Commits with `BREAKING
> CHANGE` in the commits, regardless of type, should be translated to `MAJOR`
> releases.

Notice the same tie-break this skill uses: a `BREAKING CHANGE` footer forces
MAJOR *regardless of type* — a commit that is simultaneously `feat` (additive)
and breaking is still MAJOR. That is where the "MAJOR always dominates" rule
above comes from; it is not invented for this skill, it is inherited from the
spec this skill is built on.

## This sits ON TOP of judgment infrastructure that already exists

This skill classifies. It does not replace what already decides. Two things
already exist and take precedence:

### 1. The system prompt's reversibility / blast-radius instruction

The governing instruction already present is:

> # Executing actions with care
> Carefully consider the reversibility and blast radius of actions. Generally
> you can freely take local, reversible actions like editing files or running
> tests. But for actions that are hard to reverse, affect shared systems
> beyond your local environment, or could otherwise be risky or destructive,
> check with the user before proceeding... Examples of the kind of risky
> actions that warrant user confirmation: Destructive operations...
> Hard-to-reverse operations... Actions visible to others or that affect
> shared state...

That instruction names the *dimensions* that matter: reversibility, blast
radius, visibility to others, shared state. It leaves the actual call —
"is this one of the risky ones?" — to judgment on a case-by-case basis, with
one binary outcome (check with the user, or don't). semver-gate turns those
same dimensions into a **three-way** decision procedure with a precise,
citable vocabulary, and a third state (MINOR: act, but flag) between "just do
it" and "stop and ask" that the source instruction doesn't spell out on its
own.

### 2. An autoMode permission classifier, where one is configured

Where a settings.json `autoMode` classifier already exists, it is a set of
**pre-computed verdicts for specific actions in specific repos** — the output
this skill's reasoning procedure would produce, already cached so it doesn't
need re-deriving every time. A real example, from a `dnd-campaign-companion`
repo's classifier:

- `soft_deny`: `Bash(pnpm db:push:*)` — "schema push bypassing the
  generate/migrate/journal workflow the drizzle-migration-checker enforces,"
  and `Bash(pnpm db:migrate:deploy:*)` — "applies migrations against the
  production-gated (`VERCEL_ENV`) runner." Both are MAJOR-class calls
  someone already made *for you*: they change the durable shape of a shared
  database, in a way another person (or a future you) depends on staying
  correct, without the reviewed generate → migrate → journal path.
- An `environment` block distinguishing **protected/default branches** and
  **sensitive remote targets** (anything matching `prod`/`production` as a
  whole word/segment) — both MAJOR-shaped by definition, since both are
  exactly "visible to others" / "shared state" — from a **routine allowlist**
  of commands needing no confirmation at all: `pnpm dev`, `lint`, `test`,
  `db:generate`, `db:migrate` (local), `seed`, `probe`. That allowlist is the
  PATCH tier, already classified: local, reversible, nothing outside the
  sandbox notices.

**Order of authority: a hardcoded rule always wins.** If an action already
matches a `soft_deny`, a protected-branch check, a sensitive-remote-target
pattern, or a routine allowlist entry, that verdict is the answer — don't
re-derive it, and don't let this skill's reasoning talk you out of it.
semver-gate exists for the actions that *aren't* already pre-classified, and
as a sanity check on whether an existing hardcoded rule still classifies
correctly (the `dnd-campaign-companion` entries above are literally what
"correctly classified" looks like — use them as the calibration standard).

## The mapping

| Class | Spec definition (what it means here) | What it looks like as an agent action | What you do |
|---|---|---|---|
| **PATCH** | "backward compatible bug fix... an internal change that fixes incorrect behavior" | Local, reversible, no observable change to anything outside your own edit loop. Nobody downstream can tell the difference except that something broken now works. | **Act.** Don't ask, don't hedge. Mention it in your summary so it's part of the record — but the mention is documentation, not a gate. |
| **MINOR** | "new, backward compatible functionality... introduced in a backward compatible manner" | Additive and visible: it changes what exists, but doesn't remove, break, or override anything that was there before. Real ambiguity may exist about *how* to do it. | **Act**, but flag it prominently — don't bury it in the summary. If there's genuine ambiguity about which additive path is right, name the alternative and your reasoning. This is a disclosure, not a blocking question. |
| **MAJOR** | "any backward incompatible changes... introduced to the public API" | Irreversible, destroys or overwrites existing state, changes what's visible to others outside your sandbox, or breaks a contract (a schema, a branch-protection rule, a production runtime, another person's in-flight work) that something or someone already depends on. | **Stop.** State the action, why it's MAJOR-class, and the least-destructive alternative if one exists. Wait for an explicit answer to *this* action — not an adjacent earlier "yes," and never a workaround for a block. |

## Worked calibration example: the enforce_admins episode

A real session did this correctly under real pressure, and it's worth holding
up as the calibration standard for what "acting like this" looks like in
practice.

The user asked to admin-merge a pull request by disabling GitHub's
`enforce_admins` branch-protection setting. Taken at face value, "merge it" is
a MINOR-or-lower request — it sounds like routine repo housekeeping. But the
*mechanism* required to reach it — disabling `enforce_admins` — is MAJOR-class
on its own terms: it's a repo-wide safety-gate override, explicitly documented
in that repo's own governance file as deliberate protection for a destructive
skill. **Classify the action actually being taken, not the phrasing of the
request that leads to it** — a MINOR-sounding ask can still require a
MAJOR-class mechanism, and the mechanism is what gets classified.

The agent recognized this and stopped to ask via a structured question tool,
even though the user had just said "merge." Re-asked, the user confirmed the
specific mechanism. The agent attempted it, hit a real API 503 across several
retries (a transient failure, not a new classification event — retrying a
flaky call is not the same as routing around a block), and then hit something
different: a **policy-level classifier denial** — a separate layer blocking
that exact same action for a *structural* reason, independent of the user's
confirmation: this kind of guardrail-disabling write isn't something automated
tooling should do unattended, full stop.

The agent asked again — it did not treat the user's earlier "yes" as
authorization to find a way around the new block, and it did not silently
retry into a different mechanism that might dodge the same policy. This time
it offered the least-destructive alternative: approve the pending deployment
through the normal UI instead of disabling protection. That's what the user
actually chose.

The pattern to hold onto:

- **A user's imperative doesn't auto-authorize the mechanism.** "Just merge
  it" classifies the *request*; the *mechanism* gets classified separately,
  and the more MAJOR of the two governs.
- **One confirmation covers the class of action asked about, not every block
  encountered while attempting it.** A structural denial hit mid-attempt is a
  new fact, not an obstacle to route around using the earlier "yes."
- **A MAJOR-class stop should always arrive with the least-destructive
  alternative already identified** — not a bare "can I?" but "here's the risky
  path, here's a safer one that gets you most of the way."
- **Time pressure never downgrades the class.** "Just do it" is a request for
  speed, not a reclassification of the mechanism from MAJOR to MINOR.

## How to apply this in the moment

1. **Name the action in one sentence.** Not the user's request — the actual
   mechanism: "push this branch," "run `db:push` against the dev database,"
   "disable `enforce_admins`," "overwrite this file."
2. **Check hardcoded rules first.** Protected/default branch? Sensitive remote
   target (prod/production as a whole word or segment)? An explicit
   `soft_deny` or routine-allowlist entry? If a rule already exists, that
   verdict wins — skip to step 4.
3. **If not pre-classified, ask the spec's own three questions, aimed at the
   action instead of an API:**
   - Can this be undone by me, cheaply, with nothing outside my sandbox
     noticing? → **PATCH**.
   - Does it add something new and visible without removing, breaking, or
     overriding anything that existed before — and is there real ambiguity in
     *how* to do it? → **MINOR**.
   - Does it destroy or overwrite state, change what's visible to others, or
     touch a contract that something or someone else already depends on
     (a schema, a protection rule, a production runtime, another person's
     work)? → **MAJOR**, regardless of the other two answers — MAJOR
     overrides the same way a `BREAKING CHANGE` footer overrides `feat`.
4. **Act accordingly.** PATCH: do it, mention it later. MINOR: do it, flag it
   clearly, name the live alternative if one existed. MAJOR: stop, name the
   action and why it's MAJOR and the least-destructive alternative if one
   exists, then wait for an explicit answer to *this* action.

## What this explicitly does not do

- It does not replace the system prompt's reversibility/blast-radius
  instruction or a configured `autoMode` classifier — read those first, every
  session. This gives the cases they leave to judgment a precise vocabulary
  and a tie-break rule (MAJOR dominates), nothing more.
- It is not a literal versioning tool; nothing here bumps a real package
  version. MAJOR/MINOR/PATCH are borrowed for their exact, spec-defined
  meaning (see the quotes above), not as a loose metaphor — so "this feels
  kind of major" is a misuse. Anchor every call back to the spec language:
  does it break a contract someone else depends on, yes or no.
