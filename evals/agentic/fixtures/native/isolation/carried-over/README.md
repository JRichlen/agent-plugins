# `isolation/carried-over/` — T27's negative control

A "fresh" session whose only evidence of freshness is a different session id.
The workspace still holds the previous card's artifacts, which is where the real
contamination lives (`.claude/`, `.redgate/`, scratch dirs). `leaked-artifact.txt`
and `dot-claude-state.json` stand in for those: an isolation check that compares
ids alone reports this workspace as clean.

`adapters.check_fresh_isolation` refuses it, because
`protocols.diff_tree(before, after)` is non-empty.
