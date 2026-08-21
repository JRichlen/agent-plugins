# Mid-round fact lookups

Load this only when a question in the current round actually turns on a fact
you don't have — current file content, a library's real API surface, an
existing repo convention, a config value. Most rounds need none of this.

## The rule: only the dependent question waits

A fact lookup blocks *only* the question(s) downstream of that unresolved
fact. The rest of the round's frontier is not gated by it — ask everything
else in the round now, note which question is pending the lookup, and fold its
answer in once you have it (as part of the current round if it arrives before
the user replies, or as the first item of the next round if it doesn't).
Never stall an entire round because one branch needs a lookup.

## Direct tools first

A fact lookup is not automatically a subagent job. Read the file. Grep the
repo. Fetch the doc page. Check the existing convention directly with whatever
tools the harness already gives you — that is almost always faster and cheaper
than dispatching anything.

## Subagent dispatch is a convenience, not a dependency

If a subagent-spawning tool happens to be available *and* the lookup is the
kind that benefits from isolation — a broad repo scan, comparing several
candidate sources, something that would otherwise eat a lot of the main
session's context — dispatching one is a reasonable shortcut.

This is explicitly **not** a hard gate the way second-opinion's subagent
requirement is. If no subagent tool exists, or the lookup is small, just use
direct tools. Never decline the question, never fabricate the fact, and never
present an unresolved fact as resolved to keep the round moving.
