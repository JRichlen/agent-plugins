# Run and interpret evaluations

[docs/testing.md](../docs/testing.md) owns the current tier inventory, commands,
triggers, cost, required checks and evidence limits. Update it in the same PR
whenever a tier, workflow job or plugin pack changes; the cheap gate verifies
its inventory against source.

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
