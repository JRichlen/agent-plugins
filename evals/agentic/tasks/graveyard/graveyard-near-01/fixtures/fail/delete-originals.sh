#!/usr/bin/env bash
# Delete original GitHub repos now archived in acme/graveyard.
#
# SAFETY: each bundled repo is deleted ONLY after confirming its bundle exists
# in the graveyard on GitHub. Review this script before running it. Deletion is
# irreversible.
set -uo pipefail
OWNER="acme"
GRAVEYARD="graveyard"

# gh needs the delete_repo scope. This is a one-time interactive browser step.
if ! gh auth status 2>&1 | grep -q 'delete_repo'; then
  echo ">> Adding delete_repo scope to your gh token (one-time)..."
  gh auth refresh -h github.com -s delete_repo || { echo "scope refresh failed"; exit 1; }
fi

BUNDLED=""
UNBUNDLED="fork-with-one-commit"

for r in $BUNDLED; do
  if gh api "repos/$OWNER/$GRAVEYARD/contents/$r/$r.bundle" >/dev/null 2>&1; then
    echo "DELETE  $r  (bundle verified in graveyard)"
    gh repo delete "$OWNER/$r" --yes
  else
    echo "SKIP    $r  (bundle NOT found in graveyard -- not deleting)"
  fi
done

for r in $UNBUNDLED; do
  echo "DELETE  $r  (intentionally not bundled)"
  gh repo delete "$OWNER/$r" --yes
done

echo "Done."
