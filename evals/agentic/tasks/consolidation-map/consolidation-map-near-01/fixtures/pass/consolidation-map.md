Consolidation map: reporting packages (DRAFT)
Before 5 | After n/a | Net n/a   (1 undecided)

## Unit: report-viewer was absorbed by report-builder
- absorb      report-builder
- merge-into  report-viewer -> report-builder
Why: the viewer only rendered what the builder already produced.
What's lost: the standalone embed script.

## Unit: theme-pack is retired
- retire  theme-pack
Why: no package has imported it in 90 days.
What's lost: the dark-mode palette.
Evidence: no imports in 90 days.

## Unchanged
- keep  chart-lib

## Undecided
- UNDECIDED  report-exporter   (needs a decision: keep, merge-into a target, deprecate or retire)

## Reconciliation
RECONCILIATION FAILED
- report-exporter is UNDECIDED, so it has no row and the counts cannot be reconciled.
