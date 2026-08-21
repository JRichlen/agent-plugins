# Authoring checklist — before you call a scaffold done

Scaffolding gets a plugin to *valid, wired, RED*. Filling the TODOs gets it to
*green*. Neither step asks whether the prose you wrote is any good. This
checklist is the missing step: two authoring-time disciplines to apply to
`SKILL.md` (and `AGENTS.md`) before you consider the plugin finished, on top of
the invariant-first interview in the main SKILL.md.

This is about the plugin you are *writing right now* — a document that doesn't
exist yet, or is still taking shape. It is not about auditing docs that already
shipped; that's a different, maintenance-time job for a different plugin
(`docs-hygiene`), not this one.

## 1. The No-Op Test

For every paragraph, bullet, or sentence in `SKILL.md`: delete it, mentally run
the skill again, and ask whether agent *behavior* changes. If nothing an agent
would do differs with the line gone, the line didn't earn its place — cut it.

This is a stronger bar than "is it true" or "is it well-written." Plenty of
accurate, well-written prose still doesn't change behavior — restating what the
invariant already implies, narrating why a step exists instead of what to do,
or explaining background the agent doesn't need to act. All of that reads well
and does nothing. Apply the test line by line, not just once for the whole
file — a paragraph can have three sentences that pass and one that's dead
weight.

Two places worth checking hardest, because they're where padding accumulates
without anyone noticing:

- **The invariant section.** It should be the one part of the file where
  every word is load-bearing — it's what the cheap eval defends. If a sentence
  near it doesn't change what the eval checks or what the agent does when the
  invariant is at risk, it's decoration.
- **Worked examples.** A good example earns its place by resolving a real
  ambiguity (see `references/rubric.md`'s worked classifications in
  semver-gate for the pattern of an example that's still doing work). An
  example that just restates the rule in different words fails the No-Op Test
  even though it "looks" helpful.

(Source: aihero.dev — "Writing Skills for Agents.")

## 2. Progressive disclosure of instructions

`AGENTS.md` (and its `CLAUDE.md`/`GEMINI.md` symlinks) is not an ordinary doc —
every token in it loads on **every** request that touches this plugin, whether
or not that request needs it. `SKILL.md` is cheaper — a harness typically loads
it once the skill is selected — but it still front-loads onto every invocation
of the skill, not just the branch of the workflow currently in play. Both are a
fixed cost that compounds across a long session; you are budgeting tokens, not
just writing prose.

The fix is to layer, not compress: keep the top-level file legible — the
invariant, the common path, and the one or two decisions every user of the
plugin actually has to make — and move anything that's genuinely deep,
rare-path, or reference material out to `references/*.md`, loaded only when
that specific case comes up. `scaffold-plugin.sh` doesn't generate a
`references/` directory by default; add one only when the split is earned (see
grill-me's three-file split for deep techniques invoked in some cases,
semver-gate's one-file split for a companion rubric, and tracer-bullets'
zero-file choice for a single coherent procedure — match the plugin you're
actually writing, don't force a split that isn't there).

Two smells that mean you're not disclosing progressively:

- **A `SKILL.md` that's long because it explains everything up front**,
  including branches most invocations never take. If a section only applies
  to an edge case, it belongs in a reference the top-level prose points to,
  not inline.
- **An `AGENTS.md` that duplicates `SKILL.md`** instead of pointing to it.
  `AGENTS.md`'s job is to be the short, always-loaded entry point; it should
  say what the plugin does and where the authoritative detail lives, not
  restate that detail.

(Sources: aihero.dev — "Writing Skills for Agents"; "A Complete Guide to
AGENTS.md.")

## Apply this before you call step 4 done

Run both passes on the scaffold's `SKILL.md` and `AGENTS.md` before you move on
to "confirm it's green" in the main workflow (step 4). A plugin can have a
fully passing `evals/cheap/checks.sh` and still carry prose that fails both
tests above — the cheap tier checks structure and the invariant's presence, not
whether every line of surrounding prose earns its keep. That judgment call is
this checklist's job, not the eval's.
