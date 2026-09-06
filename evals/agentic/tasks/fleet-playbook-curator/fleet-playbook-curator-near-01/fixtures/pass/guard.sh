#!/usr/bin/env bash
bash "$AGENTIC_REPO_ROOT/plugins/fleet-playbook-curator/skills/fleet-playbook-curator/scripts/validate-citations.sh" index.json diff.json context.json && jq -e '.claims[] | select(.repo=="o/gone-svc")' index.json >/dev/null  # GUARD_CHECK
