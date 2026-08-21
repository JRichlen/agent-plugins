# AGENTS.md — diagnosing-bugs

Diagnose a bug by writing ranked, falsifiable hypotheses before any code change, tagging temporary debug instrumentation for a zero-tolerance sweep, and gating the regression test to a red-then-green proof at the confirmed seam. Use when fixing a bug, debugging a failure, triaging an error, or the user asks to diagnose/root-cause/troubleshoot an issue.

## How to use it

Read `skills/diagnosing-bugs/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/diagnosing-bugs.md` is the entry point a user invokes.

## The invariant this plugin defends

A bug fix must never begin with a code change: a ranked, falsifiable hypothesis list — claim, evidence, falsifying test — must be written before any diagnostic or fix code. Temporary debug instrumentation must always carry the fixed, grep-able `DBGRM:` tag and must never ship untagged or unswept — `grep -rn 'DBGRM:' <scope>` must return zero lines before the fix is done. A fix must never land without a regression test gated to the actual seam, proven red-on-pre-fix / green-on-post-fix.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
