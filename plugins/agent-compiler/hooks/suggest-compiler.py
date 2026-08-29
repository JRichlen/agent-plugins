#!/usr/bin/env python3
"""UserPromptSubmit hook: point agent-building intent at the compiler.

When a prompt reads like a request to create an agent/persona/identity, add
one line of context reminding the model that the agent-compiler MCP tools
exist — so "make me a security reviewer" reliably becomes inspect + compile
instead of a hand-written persona blob. Conservative by design: no match,
no output, no noise.

Protocol: hook JSON on stdin; additionalContext JSON on stdout; exit 0.
Fail open on malformed input.
"""

import json
import re
import sys

# A creation/composition verb within reach of an agent-ish noun, or an
# explicit mention of compiling/registry. Tuned narrow: ordinary coding
# prompts ("run the agent tests") must not trigger it.
INTENT = re.compile(
    r"(?:\b(?:build|create|make|craft|design|spin\s+up|set\s+up|compose|"
    r"generate|compile)\b[\s\S]{0,60}?\b(?:agent|persona|subagent|reviewer|"
    r"identity)\b)"
    r"|\bagent[- ]?compiler\b|\bbehavior\s+registry\b|\bagentquery\b",
    re.IGNORECASE)

CONTEXT = (
    "The agent-compiler plugin is installed: agents are compiled, not "
    "hand-written. Use its MCP tools — inspect (find exact module ids), "
    "compile (typed AgentQuery -> hashed AgentImage; needs an effect "
    "ceiling), explain, render — or /agent-compile. Follow the "
    "agent-compiler skill: normalize intent into a query, and add missing "
    "behavior to the registry rather than pasting prose into a rendered "
    "agent.")


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 — fail open
        return 0
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str) or not INTENT.search(prompt):
        return 0
    # additionalContext is read top-level for UserPromptSubmit; the
    # hookSpecificOutput form is kept alongside for older readers.
    print(json.dumps({
        "additionalContext": CONTEXT,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": CONTEXT,
        },
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
