#!/usr/bin/env bash
# Linux GitHub-hosted runner setup. No provider keys or personal profiles.
set -euo pipefail
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${GITHUB_ENV:?GITHUB_ENV is required}"
: "${GITHUB_PATH:?GITHUB_PATH is required}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tools="$RUNNER_TEMP/pinned-tools"
mkdir -p "$tools"
cp "$root/ci/tools/package.json" "$root/ci/tools/package-lock.json" "$tools/"
sudo apt-get update -qq
sudo apt-get install -y bubblewrap patch
npm ci --prefix "$tools" --ignore-scripts --no-audit --no-fund \
  --userconfig "$root/ci/tools/empty.npmrc" --registry https://registry.npmjs.org
# Static version inspection does not initialize the CLI or its analytics.
node - "$tools/node_modules" <<'JS'
const fs = require('fs');
const path = require('path');
for (const pkg of ['promptfoo','@anthropic-ai/claude-code','@openai/codex']) {
  const data = JSON.parse(fs.readFileSync(path.join(process.argv[2],pkg,'package.json'),'utf8'));
  process.stdout.write(pkg + ' ' + data.version + '\n');
}
JS
echo "PROMPTFOO_HOME=$tools/node_modules/promptfoo" >> "$GITHUB_ENV"
echo "$tools/node_modules/.bin" >> "$GITHUB_PATH"
# Existing sandbox adapters deliberately allow only /usr/bin:/bin.
sudo ln -sf "$(command -v node)" /usr/bin/node
python3 "$root/evals/redteam/bin/provision-logger.py" \
  --promptfoo-home "$tools/node_modules/promptfoo" --apply
bash "$root/ci/provision-bubblewrap.sh"
