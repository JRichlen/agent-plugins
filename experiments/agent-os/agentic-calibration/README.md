# Agent OS agentic trajectory calibration

This is a separate cost/quality tier from the controlled paired follow-up. It runs nine bounded Luna episodes: three representative Agent OS tasks at `low`, `medium`, and `high` reasoning effort. Each episode may make at most four model turns, uses only deterministic read-only function tools, and receives one blind structured Luna judgment.

The run has a $1.00 hard cap. It preserves every request, response, reasoning metadata item, tool call/result, stop condition, token count, latency, and `usage.cost`. `cost-baseline.json` reports costs by effort, role, scenario, and episode; `trajectories.json` and per-episode raw files are the trajectory-test evidence.

This calibration measures a small bounded agent loop, not an unbounded production agent. It intentionally excludes web access, mutation, retries, subagents, and provider fallbacks so the first baseline is reproducible.
