#!/usr/bin/env bash
#
# generate-delete-script.sh — emit a SAFE, self-verifying deletion script.
#
# Deleting a GitHub repo is irreversible, so this never deletes anything itself.
# It prints a script (to stdout) that the *user* reviews and runs. For each
# bundled repo, the generated script re-checks that the bundle actually exists
# in the graveyard on GitHub before deleting the original — a repo is never
# deleted unless its backup is provably present.
#
# Usage:
#   generate-delete-script.sh <owner> <graveyard-repo> \
#       --bundled  "repo1 repo2 ..." \
#       [--unbundled "repoA repoB ..."]  > delete-originals.sh
#
#   --bundled    repos backed up into the graveyard (guarded delete)
#   --unbundled  repos to delete WITHOUT a backup — empty repos or forks you
#                deliberately chose not to archive (deleted only after the
#                guarded set; listed explicitly so nothing is silent)
#
# Requires: gh (authenticated) at RUN time, not generation time.
set -uo pipefail

die() { echo "error: $*" >&2; exit 2; }

[ $# -ge 3 ] || die "usage: generate-delete-script.sh <owner> <graveyard-repo> --bundled \"...\" [--unbundled \"...\"]"

OWNER="$1"; GRAVEYARD="$2"; shift 2
BUNDLED=""; UNBUNDLED=""
while [ $# -gt 0 ]; do
  case "$1" in
    --bundled)   BUNDLED="${2:-}"; shift 2 ;;
    --unbundled) UNBUNDLED="${2:-}"; shift 2 ;;
    *) die "unknown arg: $1" ;;
  esac
done
[ -n "$BUNDLED$UNBUNDLED" ] || die "nothing to delete: pass --bundled and/or --unbundled"

# Repo names become attacker-influenceable input to a script the user later runs
# with a delete_repo-scoped token. GitHub repo names are restricted to
# [A-Za-z0-9._-]; anything else — a shell metachar, a quote, whitespace inside a
# single name, a non-ASCII homoglyph — is either impossible or a quote-breakout
# attempt, so reject it here rather than embed it in the emitted script. The
# --bundled/--unbundled values are space-separated LISTS, so validate per token.
validate_names() {
  local _list="$1" _label="$2" _n
  for _n in $_list; do   # intentional word-split: space-separated repo list
    case "$_n" in
      *[!A-Za-z0-9._-]*) die "illegal $_label repo name '$_n': GitHub repo names allow only A-Za-z0-9._-" ;;
    esac
  done
}
validate_names "$BUNDLED"   bundled
validate_names "$UNBUNDLED" unbundled

cat <<EOF
#!/usr/bin/env bash
# Delete original GitHub repos now archived in $OWNER/$GRAVEYARD.
#
# SAFETY: each bundled repo is deleted ONLY after confirming its bundle exists
# in the graveyard on GitHub. Review this script before running it. Deletion is
# irreversible.
set -uo pipefail
OWNER="$OWNER"
GRAVEYARD="$GRAVEYARD"

# gh needs the delete_repo scope. This is a one-time interactive browser step.
if ! gh auth status 2>&1 | grep -q 'delete_repo'; then
  echo ">> Adding delete_repo scope to your gh token (one-time)..."
  gh auth refresh -h github.com -s delete_repo || { echo "scope refresh failed"; exit 1; }
fi

BUNDLED="$BUNDLED"
UNBUNDLED="$UNBUNDLED"

for r in \$BUNDLED; do
  if gh api "repos/\$OWNER/\$GRAVEYARD/contents/\$r/\$r.bundle" >/dev/null 2>&1; then
    echo "DELETE  \$r  (bundle verified in graveyard)"
    gh repo delete "\$OWNER/\$r" --yes
  else
    echo "SKIP    \$r  (bundle NOT found in graveyard -- not deleting)"
  fi
done

for r in \$UNBUNDLED; do
  echo "DELETE  \$r  (intentionally not bundled)"
  gh repo delete "\$OWNER/\$r" --yes
done

echo "Done."
EOF
