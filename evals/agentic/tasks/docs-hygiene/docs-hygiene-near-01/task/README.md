# Task

`AGENTS.md` claims the service authenticates with API keys. The code under `auth/` shows a JWT-bearer verifier as the main path, but a legacy API-key fallback still guards one old internal endpoint -- it's genuinely unclear which one `AGENTS.md` is meant to describe as current.

## Paraphrase variants (holdout)

1. AGENTS.md says API keys, the code mostly shows JWT with one legacy API-key path left -- which is right?
2. Auth docs and auth code disagree, but there's a real legacy path making it genuinely ambiguous which is current.

## Baseline framing (no-skill arm)

The no-skill baseline gets the same instruction file and repo tree and a plain read/edit capability, no staleness heuristic -- it may still catch and fix the stale path on its own initiative.
