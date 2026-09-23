# Reusable single-turn behavioral eval template

The cheap tier proves a plugin's **scripts** are safe in isolation. The behavioral
tier proves the plugin's **prose** actually steers a model toward that safe
behavior. This template is the starting point for that second tier: copy it, fill
in three TODOs, and you have a working promptfoo suite that fails when the prose
drifts.

The graveyard plugin's own behavioral tier (`plugins/graveyard/evals/promptfoo/`) is the worked
reference — read it alongside this template.

## What you get

- `prompt.template.txt` — a generic single-turn harness prompt. It injects the
  skill text as `{{skill}}` and the user request as `{{question}}`, and tells the
  model to lay out its **complete** plan in one reply (no tool loop).
- `promptfooconfig.template.yaml` — the config: cheap subject model under test, a
  separate-family Anthropic grader (Haiku), `max_tokens: 8192`, and one example `llm-rubric` test.

## How to adopt it

1. Copy both files into your plugin's eval directory and drop the `.template`:
   ```sh
   mkdir -p plugins/<plugin>/evals/promptfoo
   cp evals/templates/behavioral/prompt.template.txt \
      plugins/<plugin>/evals/promptfoo/prompt.txt
   cp evals/templates/behavioral/promptfooconfig.template.yaml \
      plugins/<plugin>/evals/promptfoo/promptfooconfig.yaml
   ```
2. Fill the three TODOs in `promptfooconfig.yaml`:
   - `description` — name the plugin/skill under test.
   - `defaultTest.vars.skill` — the `file://` path to the authoritative prose
     (usually `SKILL.md`). Injecting the real file is the whole point: a rewrite
     that weakens a rule fails here instead of shipping.
   - `tests` — one test per behavior the prose must produce. Phrase each rubric
     around the **invariant**, and state the FAIL condition explicitly so the
     grader has a clear bar.
3. Run it:
   ```sh
   cd plugins/<plugin>/evals/promptfoo
   OPENROUTER_API_KEY=... ANTHROPIC_API_KEY=... npx promptfoo@latest eval
   ```

## Why the template is shaped this way

- **Single-turn.** promptfoo captures one completion with no tool-execution loop
  feeding results back. The prompt tells the model to lay out the entire plan in
  one shot, so the rubric can grade the whole archive→verify→act arc rather than
  a first step that "would have" continued.
- **`max_tokens: 8192`.** Smaller budgets truncate mid-plan — the model spends the
  budget on preamble and never reaches the step the rubric checks, failing a valid
  plan for the wrong reason. 8192 fits a complete walkthrough. Tune down only if
  your plans are genuinely short.
- **Separate grader, cheap subject.** The subject is deliberately a cheap model —
  the question is whether a model *given the skill* behaves safely. The grader is
  kept on a separate Anthropic model (Haiku, chosen for cost) because a grader
  from the subject's family, or a flaky one, flips pass/fail unreliably and hollows
  out the tier. Keep the grader an `anthropic:messages:` slug: the CI
  `grader-model` job resolves exactly that marker to confirm it's a real model id.
- **Rubrics target invariants, not wording.** Grade the behavior the prose must
  produce, so the eval survives prose rewrites and only fails on real regressions.
