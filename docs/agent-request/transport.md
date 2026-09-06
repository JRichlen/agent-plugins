# Transport mapping

The canonical contract is adapter-neutral. `transport.py` maps canonical ASCII JSON into two headers:

- `X-Agent-Request-Schema: agent-request/v1`
- `X-Agent-Request-Metadata: <base64url canonical JSON>`

Before encoding, the sender validates the closed context-free envelope shape, so unknown fields, prompt-like free-form data, malformed values, and incomplete requests cannot enter these headers. The mapper caps canonical metadata at 4,096 bytes, encoded value at 6,144 characters, and the observed header collection at 64 fields. Decoding rejects duplicate metadata headers and duplicate JSON members, noncanonical JSON bytes, CR/LF, malformed base64, missing metadata, and unknown versions. `openai_request_kwargs()` returns only an `extra_headers` mapping: endpoint, authorization, prompt body, retries, and provider options remain outside the metadata contract.

Decode first, then run semantic validation with adapter-supplied `TrustedContext`. Do not derive trusted context from these headers. A terminating proxy must reject duplicate headers before coalescing and must not forward metadata beyond its intended policy boundary.

## Aperture handoff

An Aperture adapter would need to authenticate a configured issuer, derive trusted context, call the same semantic validator, enforce the returned coarse capability decision, and maintain durable replay state. Its product version, account features, identity source, policy language, header behavior, and deployment permissions are **not yet version/account-verified**. Infrastructure must consume the canonical schema rather than copy its enums and approval logic. No deployed Aperture API or configuration is claimed here.
