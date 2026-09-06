#!/usr/bin/env python3
"""Offline regression guard for the shared OpenRouter subject config contract.

Promptfoo 0.122.0 literal-merges config.passthrough into its OpenAI-compatible
request body. GLM is not recognized by its reasoning-model-name classifier, so
config.reasoning_effort would be silently omitted. This test checks the native passthrough configuration contract without making a
request; it does not execute Promptfoo or a live transport.
"""
from pathlib import Path
import sys

try:
    import yaml
except ImportError as error:
    raise SystemExit("PyYAML is required for subject provider config test") from error

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = (
    ROOT / "plugins/jori/evals/promptfoo/promptfooconfig.yaml",
    ROOT / "evals/routing/promptfooconfig.yaml",
    ROOT / "evals/routing/trajectory/promptfooconfig.yaml",
)
MODEL = "openrouter:z-ai/glm-5.3-flash"
EXPECTED = {"reasoning": {"effort": "max"}}

for path in CONFIGS:
    config = yaml.safe_load(path.read_text())["providers"][0]
    assert config["id"] == MODEL, (path, config["id"])
    provider = config["config"]
    assert "reasoning_effort" not in provider, (path, provider)
    assert provider.get("passthrough") == EXPECTED, (path, provider.get("passthrough"))

    # Equivalent to Promptfoo's getOpenAiBody: build normal fields first, then
    # literal-merge config.passthrough (chat.ts 0.122.0 lines 284-345).
    body = {"model": MODEL, "messages": [{"role": "user", "content": "probe"}]}
    if "max_tokens" in provider:
        body["max_tokens"] = provider["max_tokens"]
    body.update(provider["passthrough"])
    assert body["reasoning"] == {"effort": "max"}, (path, body)
    print(f"PASS {path.relative_to(ROOT)} contains native OpenRouter reasoning=max passthrough")
