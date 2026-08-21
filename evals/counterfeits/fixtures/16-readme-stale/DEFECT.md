# Counterfeit: README.md stops naming a registered plugin

**Gate exercised:** cheap tier section 5b — README documents every registered
plugin.

**Defect:** `README.md` is edited so it no longer mentions `sample-guard`
anywhere, while `marketplace.json` still registers it. This is the exact shape
of the real staleness found in `README.md` before this gate existed — a
plugin ships and gets registered, but the hand-maintained table never catches
up.

EXPECT_FAIL_SUBSTRING=registered in marketplace.json but not named in README.md
