#!/usr/bin/env bash
grep -qi 'side-project.*archive' recommendation.md && grep -qi 'typo-test.*safe to delete' recommendation.md && grep -qi 'webhook-fork.*safe to delete' recommendation.md  # GUARD_CHECK
