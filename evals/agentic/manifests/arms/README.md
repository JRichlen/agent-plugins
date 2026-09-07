# `manifests/arms/*.json` — per-plugin arm manifests (registry lane, T16/T17)

One file per live roster plugin (25 today, regenerate on a roster change --
these are DERIVED artifacts, not hand-authored; see
`evals.agentic.framework.pairing`). Each document:

```
{
  "plugin": "<name>",
  "directory": "plugins/<name>",
  "version": "<plugin.json version>",
  "derived_capabilities": [Capability.to_dict(), ...],   # pairing.discover_plugin_capabilities
  "estimand_availability": {...},                         # pairing.estimand_availability()[plugin]
  "full_package_arm": Arm.to_dict(),                      # Estimand.FULL_PACKAGE, role=treatment
  "baseline_arm": Arm.to_dict()                           # Estimand.BASELINE, role=baseline
}
```

`arm_source_card` names the real card whose author-curated `capabilities`
built these two arms (contract §3.11's precedence rule: an author-curated
card always wins over blind discovery) -- the plugin's own `-pos-01` card
when one exists, which as of this generation is every one of the 25 roster
plugins. A plugin that gains a card later, or loses its only positive card,
regenerates from a throwaway "survey" `Card` instead, whose `capabilities`
come straight from `discover_plugin_capabilities` (real, not curated).

Every pair committed here was verified with `pairing.assert_exposure_parity`
at generation time -- a manifest pair that would fail parity is never
committed. `realized_tree` is empty for every `baseline_arm` (a no-skill
baseline materializes no plugin-owned files) and non-empty for
`full_package_arm` whenever the plugin ships skill/command prose or a
`hooks/hooks.json` (script/mcp capabilities are captured entirely by
`allowed_tools`, never by a `realized_tree` entry -- see
`pairing._materialize_capability`'s docstring).

Regenerate one plugin's pair with:

```
python3 -c "
import pathlib, tempfile
from evals.agentic.framework import io, registry, validate, pairing
from evals.agentic.framework.contract import Estimand

root = io.repo_root()
ref = next(r for r in registry.derive_roster(root) if r.name == 'graveyard')
card = next(c for c in validate.load_cards(root) if c.card_id == 'graveyard-pos-01')
with tempfile.TemporaryDirectory() as tmp:
    ws = pathlib.Path(tmp)
    full = pairing.build_arm(card, Estimand.FULL_PACKAGE, (ref,), workspace=ws)
    base = pairing.build_arm(card, Estimand.BASELINE, (), workspace=ws)
print(full.to_dict())
print(base.to_dict())
"
```

CV-16: `arm_id` (`pairing.deterministic_arm_id`) is a pure function of an
arm's configuration, not a fresh `uuid4` per call -- rebuilding the SAME
configuration always reproduces the SAME `arm_id`, so the two `Arm.to_dict()`
calls above reproduce this file's `full_package_arm`/`baseline_arm` blocks
exactly (`tests/test_pairing.py::CommittedManifestsAreReproducible` asserts
this for `graveyard.json`). `derived_capabilities`/`estimand_availability`/
`arm_source_card` are assembled around those two `Arm`s by the same
generator; regenerating the full 25-file set follows the same shape per
plugin.

Counterfeit fixture `25-agentic-exposure-parity` (contract §8.8) mutates a
copy of `graveyard.json`'s `baseline_arm.allowed_tools`, adding a tool that
is not the declared `generic_equivalent` of any `full_package_arm`
capability -- the "unmatched widening" defect `pairing.assert_exposure_parity`
must reject.
