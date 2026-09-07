# Task

Implement a small config-validation function. Work under Red Gate discipline:
pin explicit, checkable criteria BEFORE writing any implementation, prove the
gate is genuinely red first, then do the work, then let an independent pass
verify it.

Acceptance (do not skip the ARM stage to get here faster): `artifacts/
config.py` defines `validate_config(cfg)`, which raises `KeyError` when the
required `name` key is missing from `cfg` -- proven inside a pinned, proven-
red Red Gate run.
