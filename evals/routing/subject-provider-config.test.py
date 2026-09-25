#!/usr/bin/env python3
"""Offline regression guard for the shared OpenRouter subject config contract.

Every guarded pack uses the tier's one subject model. When a pack bounds
reasoning, it does so with a numeric passthrough reasoning.max_tokens cap that
leaves room for the answer, never with reasoning_effort: Promptfoo 0.122.0
emits reasoning_effort only for model names its own classifier recognises, and
it literal-merges config.passthrough into the request body. This test checks
the configuration contract without making a request; it does not execute
Promptfoo or a live transport.
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
MODEL = "openrouter:qwen/qwen3.8-flash"
MIN_ANSWER = 512

for path in CONFIGS:
    config = yaml.safe_load(path.read_text())["providers"][0]
    assert config["id"] == MODEL, (path, config["id"])
    provider = config["config"]
    assert "reasoning_effort" not in provider, (path, provider)
    ceiling = provider.get("max_tokens")
    assert isinstance(ceiling, int) and ceiling > 0, (path, ceiling)

    # Equivalent to Promptfoo's getOpenAiBody: build normal fields first, then
    # literal-merge config.passthrough (chat.ts 0.122.0 lines 284-345).
    body = {"model": MODEL, "messages": [{"role": "user", "content": "probe"}], "max_tokens": ceiling}
    body.update(provider.get("passthrough") or {})
    reasoning = body.get("reasoning")
    if reasoning is not None:
        assert set(reasoning) == {"max_tokens"}, (path, reasoning)
        cap = reasoning["max_tokens"]
        assert isinstance(cap, int) and 0 < cap <= ceiling - MIN_ANSWER, (path, cap, ceiling)
    print(f"PASS {path.relative_to(ROOT)} uses {MODEL}"
          + (f" with a numeric reasoning cap {reasoning['max_tokens']}/{ceiling}" if reasoning else " with no reasoning override"))
