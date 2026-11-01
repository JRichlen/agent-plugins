TIER: haiku   (why: bulk; advisory)
OBJECTIVE: find the one risky setting in services/notify.conf | PURPOSE: complete the four-service config audit
CONTEXT: the config audit has one task per service; read services/notify.conf. The risky settings are a default admin password, certificate verification off, a wildcard CORS origin, or a request timeout of 0.
SCOPE: IN: services/notify.conf OUT: every other file (touch nothing outside the output path)
TOOLS ALLOWED: read, write. Not allowed: session control, messaging, scheduling, spawning agents.
SEARCH BUDGET: 0 searches, 0 fetches.
RULES: name the setting key and value exactly as written; do not report a look-alike setting.
OUTPUT PATH: out/notify.md
RETURN: at most 200 words in the return brief format. Do not paste the full output.
DONE WHEN: out/notify.md exists, is non-empty and names the one risky setting.
IF BLOCKED: write what you have, say what blocked you, stop.
PREVIOUS ATTEMPT: the handback said done but out/notify.md was never written.
