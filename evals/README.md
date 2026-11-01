# Run and interpret evaluations

[docs/testing.md](../docs/testing.md) owns the current tier inventory, commands,
triggers, cost, required checks and evidence limits. Update it in the same PR
whenever a tier, workflow job or plugin pack changes; the cheap gate verifies
its inventory against source.

## Choose the next check

| Changed surface | Start with | Then inspect |
|---|---|---|
| User docs or generated site | `python3 ci/check_docs.py`, page builders `--check` | Rendered navigation and readable wide/narrow layouts |
| Workflows, selection or capture | `python3 -m unittest discover -s ci/tests -p 'test_*.py'` | [CI gates, cost and artifacts](../ci/README.md) |
| Source candidate packaging | `python3 -m unittest discover -s ci/tests -p 'test_release.py'` | [Candidate boundary](../release/README.md) |
| One plugin | Its cheap pack, then the whole cheap gate | Applicable behavior, controls and host evidence in the inventory |
| Skills, safety or evaluation semantics | Whole cheap gate and the relevant controls | Required demonstrations, deep/behavioral coverage and explicit paid authority |

These are starting points, not substitutions for required checks. The exhaustive
[coverage reference](../docs/testing.md) remains canonical. A missing applicable
check is a reported gap rather than permission to skip it silently.

Start with the free deterministic gate:

```sh
evals/cheap/run.sh
```

For an isolated registered package:

```sh
evals/cheap/run-one.sh <plugin-name>
```

Use the applicable behavioral, counterfeit, agentic, scale and native-host tiers
from the inventory. A skipped tier is not a passed experiment. Offline fixtures
and source assertions test mechanics; model trials and human judgments are
separate evidence. Report actual hosts, coverage, faults and limits. Do not
claim broad efficacy or universal host parity from a green structural check.

Model calls require cost authorization and any applicable disclosure consent.
Keep paid labels, provider boundaries and workflow gates intact. Do not substitute
an unpinned evaluator or suppress failed checks to obtain a green result.
