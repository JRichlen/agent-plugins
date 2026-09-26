# Deliverable interface

Write `estimate.json` with `metric: pass@k`, integer `n`, `k`, `successes`, numeric `estimate` between zero and one, and `evidence_scope: supplied-offline-fixture`. Compute the without-replacement probability from the supplied attempts. A separate optional `eval-plan.json` may record surface/rung/blind-spot/red-control strategy; it does not determine utility.

The estimate must be a finite JSON number with absolute error at most `1e-6`; rounding to six decimal places is sufficient. Boolean values are not numeric estimates. Integer counts must remain exact.
