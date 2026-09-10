# Counterfeit: a plugin adds a fourth hook and discovery misses it

**Gate exercised:** `evals/agentic/run.sh` (offline suite), specifically T19's
hook-discovery contract in `evals/agentic/framework/protocols.py`
(`discover_hooks`), reached via the `evals/cheap/run.sh` §22 "agentic suite
(offline)" gate.

**Defect:** adds a fourth hook (a new `plugin-gamma` with a `PostToolUse`
hook) to the synthetic three-hook plugin tree the protocol lane's own
discovery test relies on
(`evals/agentic/fixtures/protocols/plugins/`). The unmutated tree has exactly
three hooks across `plugin-alpha` (two) and `plugin-beta` (one) — that count
is the whole point of T19's negative control: a `discover_hooks` that had
regressed to a hardcoded plugin list, or that cached a count instead of
re-parsing `hooks.json` files on every call, would report "3 hooks" against
this mutated four-hook tree exactly as it does against the real one, and the
regression would be invisible.

Nothing about the *shape* of the tree is broken — every `hooks.json` stays
valid JSON, every referenced handler script exists and exits 0 — so a
structural gate (JSON parses, shell parses) sees nothing wrong. The only
thing that must fail is `evals/agentic/run.sh`'s own T19 assertion that the
fixture tree carries exactly three hooks.

**Status: INERT until the integration lane lands its `evals/counterfeits/run.sh`
changes (contract §8.8).** Today, `build_root()` in `evals/counterfeits/run.sh`
does not stage `evals/agentic/**` into the synthetic root at all, and the gate
loop runs the copied `evals/cheap/run.sh`, not `evals/agentic/run.sh` — neither
of which exists as a wired entry point yet. Until the integration lane adds
`cp -R "$REPO_ROOT/evals/agentic" "$root/evals/agentic"` to `build_root()` and
wires `evals/agentic/run.sh`'s own T19 test into the always-on gate this
fixture's `mutate.sh` cannot be exercised end-to-end. It is written now,
positioned at the path staging will produce, so that landing is a pure wiring
change with no further fixture authoring required.

EXPECT_FAIL_SUBSTRING=agentic FAIL protocol: hook discovery missed
