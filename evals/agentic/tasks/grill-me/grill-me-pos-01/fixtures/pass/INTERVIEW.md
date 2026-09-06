❓ Q1 -- rollback: can the sharded store be rolled back cleanly if the migration fails?
➡️ keep the Postgres primary live in shadow-write mode until cutover is verified

Devil's-advocate: what if shadow-write itself masks a data-loss bug until cutover?

**Confirmed Decisions**
- Shadow-write until verified.

**Open Risks Accepted As-Is**
- Pagination cursor format changes for API clients.

**Deferred-for-Later**
- Long-term sharding key choice.

Please confirm this shared understanding before we start.
