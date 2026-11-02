# Documentation: choose a path

| You want to… | Start here |
|---|---|
| Try one useful task | [Getting started](getting-started.md) |
| Install one method | [Route chooser](installation.md) and [guided agent prompts](guided-installation.md) |
| Follow a change | [Bug, feature and handoff guides](guides/README.md) |
| Choose a method | [Task catalog](../README.md#choose-by-need) |
| Inspect claims | [Examples](examples/README.md) and [test evidence](testing.md) |
| Change behavior or integration | [Core](../core/OPERATING.md), [host adapters](../core/adapters/), then the owning plugin |
| Contribute | [Contribution path](../CONTRIBUTING.md), [CI](../ci/README.md), [candidate staging](../release/README.md) |

## Maintain the right source

User instructions belong in each plugin's README. Agent behavior belongs in its
SKILL and actual host entrypoints. Shared rules have their owner in
`core/ownership.json`; link to that source instead of copying policy into guides.

| Generated view | Edit | Regenerate from the repository root |
|---|---|---|
| Landing `docs/index.html` | `docs/build-index.sh`, marketplace metadata, snapshots | `bash docs/build-index.sh` |
| Gallery `docs/examples/index.html` | `docs/build-examples.sh`, `docs/examples/data/` | `bash docs/build-examples.sh` |
| Installation table | `docs/installation-routes.json` | `python3 ci/check_installation.py --write` |
| Shared site navigation | `docs/_shared/sitenav.py` | Regenerate landing/gallery and update the compiler page's shared nav |
| Packaged Core copies | `core/OPERATING.md`, `core/ownership.json` and sync rules | `python3 core/sync.py` |

Use `--check` on the two page builders to detect drift. Run documentation link
checks and inspect the rendered page at narrow and wide widths. A passing byte
comparison does not catch confusing prose, broken navigation or unreadable
diagrams. Keep diagrams paired with a text explanation and tables compact.

For installation guidance, run `python3 ci/check_installation.py` and
`python3 -m unittest ci.tests.test_installation`. These check the declared
starter resources, effects and evidence labels; they do not install a host or
prove native discovery. Recheck the inventory's official sources when changing
a route, and record the source-check date without promoting untested hosts.

The exhaustive machine-checked test inventory stays in [testing.md](testing.md).
Use the [eval selection map](../evals/README.md) to choose checks rather than
copying that inventory into every guide. Working plans and historical narratives
belong in commits/PRs once their current purpose ends.
