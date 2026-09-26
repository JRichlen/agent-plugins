#!/usr/bin/env python3
"""T12/T15 negative-control fixture: an unconditional stub verifier.

Always reports {"passed": true} regardless of workspace content. If a card
names THIS SAME script as both its outcome_verifier and its adoption_verifier,
the 2x2 outcome/adoption matrix collapses to its diagonal (n10 = n01 = 0 by
construction) -- validate_card must refuse to accept such a card.
"""
import json
import sys

if __name__ == "__main__":
    print(json.dumps({"passed": True, "reason": "stub: always true"}))
    sys.exit(0)
