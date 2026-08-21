# Counterfeit: plugin.json description drifts from the marketplace.json entry

**Gate exercised:** cheap tier section 3a — plugin.json <-> marketplace.json
description/keywords parity.

**Defect:** `plugin.json`'s `description` is changed so it no longer matches
the `description` on that plugin's entry in `marketplace.json`. This is the
exact shape of the real drift found in `orchestrate` and `graveyard` before
this gate existed — a manifest edited in only one of the two places it's
duplicated.

EXPECT_FAIL_SUBSTRING=description differs between plugin.json and marketplace.json entry
