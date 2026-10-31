#!/usr/bin/env bash
set -euo pipefail
source_bundle="$1"
scratch="$2"
mkdir -p "$scratch"
git clone --quiet --branch main "$source_bundle" "$scratch/original"
git -C "$scratch/original" bundle create "$scratch/backup.bundle" --all
git clone --quiet --branch main "$scratch/backup.bundle" "$scratch/changed"
printf 'temporary rehearsal edit\n' > "$scratch/changed/app.py"
git clone --quiet --branch main "$scratch/backup.bundle" "$scratch/restored"
git -C "$scratch/restored" diff --exit-code HEAD
cmp "$scratch/original/app.py" "$scratch/restored/app.py"
