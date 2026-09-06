# `agent-request/v1` offline contract

`agent-request/v1` is a small request-time metadata contract for coarse routing and tool policy. It carries opaque correlation identifiers and bounded enums. It never carries prompts, responses, user messages, repository content, tool payloads, credentials, hidden reasoning, or free-form labels.

The normative machine shape is [`schema.json`](../../evals/agent-request/schema.json); [`validator.py`](../../evals/agent-request/validator.py) adds cross-field and trusted-context rules JSON Schema cannot express. Unknown versions, fields, enum values, capabilities, malformed types, oversized canonical JSON, noncanonical capability lists, invalid timestamps, and TTLs over five minutes fail closed with stable error codes.

## Trust boundary

The entire request envelope is untrusted. An adapter supplies `TrustedContext` separately from authenticated transport/session policy. It pins issuer, agent, run, task, action, phase, context lane, reasoning lane, privacy class, dispatcher run and sequence, permitted parents, policy bundles, model classes, capability ceiling, current time, nonce history, and exact approval grants. A caller cannot become trusted by adding issuer or approval strings to metadata. Successful normalized output reports these values from the validated trusted context.

Validation binds every listed operational field to that context. `parent_run_id` establishes opaque provenance only; it never inherits capabilities or approval. `provenance.dispatcher_run_id` and its bounded sequence support correlation without transcript inheritance and must exactly match trusted dispatcher state. Nonces are consumed only after successful validation; adapters need durable replay state if protection must survive restart. The offline JSON fixture loader is closed and bounded, rejects malformed types, duplicate grant IDs and unknown nested fields, and remains test scaffolding rather than authentication.

## Capability and approval semantics

Capabilities are deny-by-default and capped at eight. Model, reasoning, context, phase, routing role, and Red Gate status do not grant tools.

| Class | Capability | Constraint |
|---|---|---|
| read-only | `scm:read`, `filesystem:workspace-read`, `network:http` | Must remain within the trusted ceiling. Network permission is not credential or destination permission. |
| sensitive-read | `sensitive:read` | Requires `privacy_class=sensitive` and an exact grant. |
| mutating | `filesystem:workspace-write` | Requires `phase=implement` and an exact grant. |
| publishing | `external:publish` | Requires `phase=publish` and an exact grant. |
| deployment | `deployment:operate` | Requires an exact grant. |
| host administration | `host:admin` | Requires `deployment:operate` and an exact grant. |

A `pending` approval always denies. A `granted` assertion is useful only when trusted context contains the same unexpired grant bound to issuer, agent, run, task, action, and every privileged capability requested. Stale, adjacent, replayed, cross-run, cross-task, and cross-action grants deny.

## Relation to routing and control flow

Issue #84 trigger classes decide whether a procedure is eligible to run. Issue #88's `specialist`, `envelope`, `guards`, and `interaction_owner` describe workflow composition. Neither is request-time authority. A dispatcher may use those results to choose a phase or prepare a request, but only trusted policy context supplies capabilities and exact approval.

This slice is an offline semantic core. It does not implement a genuine issuer, signature, durable replay database, dispatcher, connector grant system, gateway policy, or deployment.
