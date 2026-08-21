# wayfinder

Chart a multi-session effort as a labeled map of typed decision tickets
(grilling / prototype / research / task) with explicit dependencies and an
open frontier agents self-assign into. Plans; never executes.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install wayfinder@jrichlen
```

## What it does

wayfinder charts work too big for one session into a durable, inspectable
map: every piece of the effort becomes a ticket typed `grilling`,
`prototype`, `research`, or `task`, with its dependencies stated explicitly.
The **frontier** — every open ticket whose dependencies are all closed — is
computed fresh each time, never cached, and it's the only set that may ever
be dispatched concurrently.

The ticket store is whatever the user already has: GitHub issues (state in
issue labels, one status label per ticket) if a `gh`-backed repo is in scope,
or a local `.wayfinder/` directory of frontmattered ticket files otherwise.
Modeled directly on Jordan's `homelab-board` discipline — labels (or a
`status:` field) are the only state; any rendered view is a throwaway query
over the store, never the store itself.

wayfinder never executes the work it charts. It hands dispatch off — to the
user, to `orchestrate`, or to plain parallel agent calls — bound by one rule:
only the frontier, never a ticket whose dependency is still open.

See `skills/wayfinder/SKILL.md` for the full procedure and its "Not this"
section distinguishing wayfinder from `orchestrate` (single-session
research-and-verify fan-out, no persistent ticket state) and `grill-me`
(single-session live interrogation of one plan, no ticket store).

## License

MIT
