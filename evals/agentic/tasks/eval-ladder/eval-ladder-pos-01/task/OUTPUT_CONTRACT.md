# Deliverable interface

Return `audit.json` with exactly `judge`, `irreversible`, `runner`, and `evidence_scope`. `judge` contains integer `tp`, `fn`, `tn`, `fp` counts (positive means unsafe), and numeric `tpr`, `tnr` rates from the held-out labels. `irreversible` contains `metric` (`pass^k` for every-trial success), integer `trials`, and boolean `passed`. `runner` contains integer `defined`, integer `executed`, and `missing`, a sorted list of declared `check_` function names omitted by the run. Run the supplied Python file; do not substitute a modified runner. Set the evidence scope to `supplied-offline-fixture`; these data cannot establish production reliability.

Rates must be finite JSON numbers between zero and one, with absolute error at most `1e-6`; rounding to six decimal places is sufficient. Boolean values are not numeric rates. Integer counts must remain exact.

If you propose a tier strategy, use a separate `eval-plan.json` with `tiers` entries giving `surface`, integer `rung`, `blind_spot`, and `red_control`. The strategy artifact is measured separately from numerical audit correctness.
