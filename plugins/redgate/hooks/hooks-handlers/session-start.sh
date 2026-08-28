#!/usr/bin/env bash
# session-start.sh — surface an unfinished Red Gate run so a new session does
# not silently start a second one. Read-only; never blocks.
# PORTABILITY: Claude-Code hooks are a convenience, not a dependency — on
# another harness, read .redgate/*/manifest by hand.
set -u
for m in .redgate/*/manifest; do
  [ -f "$m" ] || continue
  slug=$(sed -n 's/^slug=//p' "$m" | head -1)
  phase=$(sed -n 's/^phase=//p' "$m" | head -1)
  round=$(sed -n 's/^round=//p' "$m" | head -1)
  case "$phase" in
    TRACE|MIDDLE) echo "redgate: run '$slug' is mid-round $round (phase=$phase) — its contract is pinned and must not be edited." ;;
  esac
done
exit 0
