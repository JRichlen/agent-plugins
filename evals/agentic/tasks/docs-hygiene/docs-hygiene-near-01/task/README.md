# Task

`AGENTS.md` claims the service authenticates with API keys. The code under `auth/` shows a JWT-bearer verifier as the main path, but a legacy API-key fallback still guards one old internal endpoint -- it's genuinely unclear which one `AGENTS.md` is meant to describe as current.
