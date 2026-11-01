#!/usr/bin/env bash
# Fresh operational profiles, no imported login/email/configuration.
set -euo pipefail
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${GITHUB_ENV:?GITHUB_ENV is required}"
profiles="$(mktemp -d "$RUNNER_TEMP/eval-profiles.XXXXXX")"
mkdir -p "$profiles/promptfoo" "$profiles/claude" "$profiles/codex"
{
  echo "PROMPTFOO_CONFIG_DIR=$profiles/promptfoo"
  echo "CLAUDE_CONFIG_DIR=$profiles/claude"
  echo "CODEX_HOME=$profiles/codex"
  echo "DISABLE_TELEMETRY=1"
  echo "DISABLE_ERROR_REPORTING=1"
  echo "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1"
  echo "PROMPTFOO_DISABLE_TELEMETRY=1"
  echo "PROMPTFOO_DISABLE_UPDATE=1"
  echo "PROMPTFOO_DISABLE_SHARING=1"
} >> "$GITHUB_ENV"
# Promptfoo 0.122 still attempts a disabled-event diagnostic; the offline
# wrapper's fail-closed proxy remains authoritative for offline invocations.
