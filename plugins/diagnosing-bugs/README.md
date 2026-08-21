# diagnosing-bugs

Diagnose a bug by writing ranked, falsifiable hypotheses before any code
change, tagging temporary debug instrumentation for a zero-tolerance sweep,
and gating the regression test to a red-then-green proof at the confirmed
seam. Use when fixing a bug, debugging a failure, triaging an error, or the
user asks to diagnose/root-cause/troubleshoot an issue.

## Where the idea comes from

Sourced from the same harvest as this marketplace's other aihero.dev-derived
skills: Matt Pocock's "How I Diagnose Bugs" (aihero.dev,
`/skills-diagnosing-bugs`). It restates "guess and check" debugging as an
actual disciplined procedure — falsifiable hypotheses ranked and written down
*before* any code changes, tagged throwaway instrumentation swept to zero
before shipping, and a regression test proven gated to the real seam rather
than just added and hoped about.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install diagnosing-bugs@jrichlen
```

## What it defends

Three checkpoints that are never allowed to soften, even though everything
else in the procedure (ranking heuristics, minimization tactics, how the
feedback loop gets tightened) is allowed to be approximate:

1. **Hypothesis-before-code.** A ranked, falsifiable hypothesis list — claim,
   evidence, falsifying test — is written before any diagnostic or fix code.
2. **Tag-before-ship.** Any temporary debug instrumentation carries the
   literal `DBGRM:` tag; a `grep -rn 'DBGRM:' <scope>` sweep must return zero
   lines before the fix ships.
3. **Seam-gated-test.** The regression test targets the exact seam found by
   minimizing the repro, proven by a red-on-pre-fix / green-on-post-fix
   check — not a coincidental higher-level test that happens to pass through
   it.

See `skills/diagnosing-bugs/SKILL.md` for the full seven-step procedure.

## License

MIT
