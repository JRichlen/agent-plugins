# Responsibility ownership before packaging

Decision source: current main `2ff596c`, including merged PR150. This replaces
the earlier nine-unit assembly design. No new package-count target is imposed.

## Designs considered

| Design | Depth | Locality | Seam placement | Decision |
|---|---|---|---|---|
| Rename full coordinator/protocol copies | Small public surface, repeated governing complexity underneath | A policy correction still changes several sources | Names conceal overlapping owners | Reject |
| Assemble nine bundles from unchanged legacy sources | Convenient distribution | Every old instruction conflict survives inside a bundle | Package seam is real but does not address responsibility duplication | Superseded |
| One short core, existing shared services, distinct task methods | Shared rules and bounded service calls hide repeated coordination/state decisions | A shared-rule correction changes one canonical source and generated copies | Authority/state, dispatch/recovery and acceptance evidence are separate real seams | Implement |

The selected refactor deletes competing governing prose rather than copying it
into a new framework. It uses the merged delegation service for actual execution,
existing continuity and claim checking, and optional acceptance helpers for their
distinct integrity behavior. The old coordinator and universal round driver are
retired as public products.

## Interfaces and ownership

The [operating core](../../core/OPERATING.md) and
[ownership index](../../core/ownership.json) are canonical. Services declare
activation, entry, exit, dependencies and evidence returned. Selected methods
carry generated read-only core copies; host adapters remain repository artifacts
until separately reviewed and activated.

Confirmed seams are task-state/provenance, bounded worker assignment and returned
evidence, and executable acceptance verification. Tests use real artifacts and
counterfactual guard mutations. A worker report is data; an independent check
requires an actual independent party.

[core/sync.py](../../core/sync.py) checks canonical projections. It does not
install instructions, select a provider, execute a task or grant authority.

## Gates and limits

Source, catalog, routing, current coverage and generated documentation must
agree. Retired names may remain only in explicit migration adapters/notices and
history. New method descriptions must not continue advertising the old products.

The mandatory free gate, relevant runtime checks and host qualification are not
waived by a design decision. Paid work remains limited to the specifically
approved automatic checks. No live setup, daemon, autonomous knowledge graph,
self-rewriting subsystem or broad adoption is introduced.

See the [complete map](plugin-consolidation-continuation.md) and
[testing inventory](../testing.md) for current scope and evidence limits.
