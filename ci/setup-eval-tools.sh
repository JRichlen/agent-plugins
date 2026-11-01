#!/usr/bin/env bash
# Linux GitHub-hosted runner setup. No provider keys or personal profiles.
set -euo pipefail
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${GITHUB_ENV:?GITHUB_ENV is required}"
: "${GITHUB_PATH:?GITHUB_PATH is required}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
python3 "$root/ci/check_toolchain.py" --root "$root"
expected_npm="$(node -p "require(process.argv[1]).packageManager.replace(/^npm@/, '')" "$root/ci/tools/package.json")"
[ "$(npm --version)" = "$expected_npm" ] || { echo "Expected npm $expected_npm from the pinned Node toolchain" >&2; exit 1; }
tools="$RUNNER_TEMP/pinned-tools"
mkdir -p "$tools"
cp "$root/ci/tools/package.json" "$root/ci/tools/package-lock.json" "$tools/"
case "${EVAL_OFFLINE_SANDBOX:-true}" in true|false) ;; *) echo 'invalid offline sandbox selection' >&2; exit 2;; esac
if [ "${EVAL_OFFLINE_SANDBOX:-true}" = true ]; then
  sudo apt-get update -qq
  sudo apt-get install -y bubblewrap patch
fi
npm ci --prefix "$tools" --ignore-scripts --no-audit --no-fund \
  --userconfig "$root/ci/tools/empty.npmrc" --registry https://registry.npmjs.org
# The locked Claude wrapper ships a placeholder. Its inspected installer only
# copies the already-installed platform binary; it makes no network/model call.
python3 "$root/ci/check_toolchain.py" --root "$root" --modules "$tools/node_modules"
node "$tools/node_modules/@anthropic-ai/claude-code/install.cjs"
python3 - "$tools/node_modules/.bin/claude" <<'PY'
import os, sys
if not os.access(sys.argv[1], os.X_OK):
    raise SystemExit("Claude launcher is not executable")
with open(sys.argv[1], 'rb') as source:
    if source.read(4) != b'\x7fELF':
        raise SystemExit('Claude platform installation did not produce a Linux ELF binary')
PY
# Static version inspection does not initialize the CLI or its analytics.
node - "$tools/node_modules" <<'JS'
const fs = require('fs');
const path = require('path');
for (const pkg of ['promptfoo','@anthropic-ai/claude-code','@openai/codex']) {
  const data = JSON.parse(fs.readFileSync(path.join(process.argv[2],pkg,'package.json'),'utf8'));
  process.stdout.write(pkg + ' ' + data.version + '\n');
}
JS
node "$root/ci/tools-smoke.cjs" "$tools/node_modules"
echo "PROMPTFOO_HOME=$tools/node_modules/promptfoo" >> "$GITHUB_ENV"
echo "$tools/node_modules/.bin" >> "$GITHUB_PATH"
# Existing sandbox adapters deliberately allow only /usr/bin:/bin.
if [ "${EVAL_OFFLINE_SANDBOX:-true}" = true ]; then
  sudo ln -sf "$(command -v node)" /usr/bin/node
fi
python3 "$root/evals/redteam/bin/provision-logger.py" \
  --promptfoo-home "$tools/node_modules/promptfoo" --apply
if [ "${EVAL_OFFLINE_SANDBOX:-true}" = true ]; then
  bash "$root/ci/provision-bubblewrap.sh"
fi
