#!/usr/bin/env python3
"""Mutant of agent-compiler's guard-compiled-agents.py: denies EVERY write.

Negative control for T20. The real guard's "allow ordinary file" test only
proves something if a guard that denies everything would fail it — this
mutant is that failing case, committed so the negative assertion has a real
artifact behind it instead of an inline string built at test time.
"""
import json
import sys


def main() -> int:
    try:
        json.load(sys.stdin)
    except Exception:  # noqa: BLE001 — still deny even on unparsable input
        pass
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "mutant: denies every write unconditionally",
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
