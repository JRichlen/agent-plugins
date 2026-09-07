#!/usr/bin/env bash
diff <(bash "$AGENTIC_REPO_ROOT/plugins/graveyard/skills/graveyard/scripts/generate-delete-script.sh" acme graveyard --unbundled "empty-mistake") delete-originals.sh  # GUARD_CHECK
