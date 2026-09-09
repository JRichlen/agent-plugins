# Counterfeit: a pack check that silently does not run

**Gate exercised:** the fail-closed pack guard (`pack_guard_on` in
`evals/cheap/helpers.sh`), installed around per-plugin pack sourcing by both
runners.

**Defect:** `sample-guard`'s cheap pack gains one extra assertion that calls a
helper **no runner defines**. Nothing structural is broken — the shell parses,
the JSON is valid, the pack exists, every other assertion still passes — so
every other gate stays green.

Before issue #120's fix this counterfeit would have been **accepted**: packs are
sourced without `set -e`, so a call to an undefined helper printed
`command not found` on stderr and execution sailed past it. The runner then
reported a green summary over a check that never ran. That was not theoretical —
`run-one.sh`, the runner the **required** install matrix uses, defined three of
the six helpers `run.sh` provided, and **253 checks across 14 plugins** were
silently skipped in the required tier while it reported success.

The other seventeen fixtures all mutate plugin *content*. This one mutates the
relationship between a pack and its *harness*, which is why the corpus did not
catch #120 on its own: a gate that cannot fail is invisible to a corpus that
only asks whether gates reject bad content.

EXPECT_FAIL_SUBSTRING=pack called an undefined command
