Consolidation map: reporting packages
Before 5 | After 3 | Net -2   (kept 2, merged-away 2, retired 1, new 0)

## Unit: report-viewer and report-exporter were absorbed by report-builder
- absorb      report-builder
- merge-into  report-viewer -> report-builder
- merge-into  report-exporter -> report-builder
Why: both only rendered what the builder already produced.
What's lost: the standalone embed script.

## Unit: theme-pack is retired
- retire  theme-pack
Why: no package has imported it in 90 days.
What's lost: the dark-mode palette.
Evidence: no imports in 90 days.

## Unchanged
- keep  chart-lib

## Reconciliation
N = K + X + R : 5 = 2 + 2 + 1   OK
M = K + W     : 3 = 2 + 0       OK
Every inventory entity appears once: OK
