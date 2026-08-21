# context-handoff

Walk the ordered continue, clear, handoff, delegate, compact decision tree at a phase boundary, and keep any handoff artifact pointer-only — settled specs, plans, ADRs, issues, commits, and diffs referenced by path or URL, never copied inline. Use this when the context window is getting full, you're wondering whether to clear or compact, you need to hand off to another harness, directory, or colleague, you've hit a phase boundary and aren't sure whether to keep going or start fresh, or you want to cache hard-won research before it's lost.

## What it is (and isn't)

At a phase boundary — the previous unit of work is settled, the next hasn't
started — there are exactly five possible moves, checked in a fixed order,
first match wins: **continue**, **clear**, **handoff**, **delegate**,
**compact**. This plugin is that ordered tree, plus the exact shape a
handoff artifact must take when the tree routes there.

It is not a fan-out planner (see `orchestrate` for how to structure a
research-and-verify subagent fan-out once you've already decided to
delegate) and it is not an end-of-day journal (see `dev-diary` for a
human-readable summary written for your future self, days later). See the
"Not this" section in `skills/context-handoff/SKILL.md` for the full
differentiation.

PORTABILITY: "subagent" above names Claude Code's Task tool / Workflow tool
as the concrete example. The discipline this plugin governs — deciding
whether to delegate at all, before deciding how — is harness-agnostic;
re-implement DELEGATE with whatever fan-out primitive your harness provides.

## How it's structured

- The decision tree itself is short (5 nodes) and read on every invocation,
  so it stays inline in `skills/context-handoff/SKILL.md` — no load-then-read
  round trip for the thing every invocation needs.
- `skills/context-handoff/references/portable-extraction.md` loads only when
  the tree resolves to HANDOFF: the pointer-only rule, the drift check, the
  handoff-file shape, the resolvability check, and the deterministic
  quoted-block size check.
- `skills/context-handoff/references/research-documenter.md` loads on its
  own separate trigger — hard-to-reach research produced mid-work,
  independent of which tree branch gets chosen: when to write `research.md`,
  what belongs in it, and its temporary lifecycle.
- `scripts/check-handoff-portability.py` is the deterministic checker for the
  HANDOFF branch's size-check rule — run it against a candidate handoff file
  before sending it:

  ```
  python3 plugins/context-handoff/scripts/check-handoff-portability.py path/to/handoff.md
  ```

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install context-handoff@jrichlen
```

## License

MIT
