# Threat model and data minimization

## Rejected counterfeits

The deterministic corpus covers unknown versions and fields; prompt-field injection; control characters and oversized identifiers; unknown, duplicate, unsorted, and high-cardinality capabilities; identity and operational-field spoofing; untrusted parents and dispatcher provenance; stale requests; nonce replay; phase/model authority escalation; pending or unknown grants; cross-run/task/action grants; stale grants; malformed trusted fixtures and duplicate grant IDs; invalid capability combinations; duplicate/malformed/oversized headers and JSON members in request or fixture files; noncanonical metadata; and CR/LF injection.

The validator returns stable non-sensitive codes. It does not echo request values, approval records, headers, or parser details. Callers should log only the code, schema version, opaque correlation identifier where policy permits, and a bounded timestamp.

## Explicit limits

- The character grammar and size limits reduce injection and accidental disclosure; they cannot prove an opaque identifier was generated without semantic content.
- Trusted context is an API boundary, not an authentication implementation. A real adapter must derive it from authenticated issuer/session policy rather than accept it from the request.
- The in-memory nonce set demonstrates replay semantics. Production replay protection needs atomic durable state, bounded retention, clock policy, and cross-instance consistency.
- Provenance is correlation, not ancestry-based delegation. Parent capabilities and approvals never transfer.
- Approval grants model exact binding in tests; this slice provides no signing, identity proof, revocation service, or human-consent UI.
- Gateway enforcement is defense in depth. Dispatchers still own task state, concurrency, retry, context budgets, tool arguments, and exact destinations.
