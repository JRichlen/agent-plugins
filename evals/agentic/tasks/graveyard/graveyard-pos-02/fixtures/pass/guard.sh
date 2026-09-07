#!/usr/bin/env bash
diff <(bash "$AGENTIC_REPO_ROOT/plugins/graveyard/skills/graveyard/scripts/generate-delete-script.sh" acme graveyard --bundled "legacy-service") delete-originals.sh  # GUARD_CHECK
