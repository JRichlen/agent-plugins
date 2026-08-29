#!/usr/bin/env bash
#
# criteria-index.sh — build (or verify) .redgate/INDEX.md, the verifier corpus
# index.
#
# Build:  criteria-index.sh [--root DIR]
# Check:  criteria-index.sh --check [--root DIR]
#
# Verifiers are the most expensive artifact a Red Gate run produces and the
# only one that resets to zero each run (gap #10, docs/research/gap-analysis.md).
# This script reads every run under .redgate/<slug>/ and writes one table row
# per criterion — run, number, status, layers, statement — so the next ARM can
# reuse a check shape that already survived instead of re-inventing it. The
# index is a POINTER CATALOG: the reusable check_cmd itself stays in the run's
# pinned CRITERIA.md, which this script never touches (read-only over runs; the
# only file it writes is .redgate/INDEX.md, outside every run dir, so the
# ratified-contract guard is never in play).
#
# Status column:
#   checkable — the criterion carries a check_cmd
#   witness   — declared WITNESS/UNVERIFIABLE (human observation, not reusable
#               as a mechanical shape)
#   demoted   — the run's gates.log records mutation control demoting this
#               criterion (it stayed green when its subject was reverted:
#               WITNESS-in-fact). NEVER reuse a demoted shape as a positive
#               control — it is in the index precisely as a warning.
#
# Output is deterministic (runs sorted by slug, criteria by number), so the
# committed INDEX.md is verifiable: --check rebuilds to a temp file and diffs,
# exiting 1 on drift — the same sync contract the example gallery uses.
#
# Exit: 0 built (or in sync); 1 --check drift; 2 usage.
set -uo pipefail

MODE=build ROOT="$PWD"
while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODE=check; shift ;;
    --root)  ROOT="${2:?}"; shift 2 ;;
    *) echo "usage: criteria-index.sh [--check] [--root DIR]" >&2; exit 2 ;;
  esac
done

RG="$ROOT/.redgate"
INDEX="$RG/INDEX.md"
mkdir -p "$RG"

emit() {
  printf '# .redgate/INDEX.md — the verifier corpus index (GENERATED; do not edit)\n'
  printf '#\n'
  printf '# Built by plugins/redgate/skills/criteria-contract/scripts/criteria-index.sh.\n'
  printf '# ARM consults this before writing check_cmds: a checkable shape from a prior\n'
  printf '# run is a candidate positive control — open that run'"'"'s CRITERIA.md for the\n'
  printf '# actual check_cmd. A demoted shape stayed green under mutation control\n'
  printf '# (WITNESS-in-fact) and must NOT be reused as proof.\n'
  printf '\n'
  printf '| run | # | status | layers | statement |\n'
  printf '|---|---|---|---|---|\n'
  local run slug crit
  for run in $(ls -d "$RG"/*/ 2>/dev/null | sort); do
    [ -f "$run/manifest" ] || continue           # not a run dir (or synthetic)
    [ -f "$run/CRITERIA.md" ] || continue
    slug="$(basename "$run")"
    # Demoted criterion numbers, from the run's gate ledger. The real record
    # reads e.g. "MUTATION CONTROL demotes #3,#4" — collect every #N on any
    # line that mentions demotion.
    demoted=" "
    if [ -f "$run/gates.log" ]; then
      demoted=" $(grep -i 'demot' "$run/gates.log" 2>/dev/null | grep -oE '#[0-9]+' | tr -d '#' | sort -un | tr '\n' ' ')"
    fi
    n="" stmt="" layers="" status=""
    flush() {
      [ -n "$n" ] || return 0
      case "$demoted" in (*" $n "*) status=demoted ;; esac
      printf '| %s | %s | %s | %s | %s |\n' "$slug" "$n" "${status:-unknown}" "${layers:--}" "$stmt"
    }
    while IFS= read -r line || [ -n "$line" ]; do
      case "$line" in
        "## #"*)
          flush
          n="$(printf '%s' "$line" | sed 's/^## #\([0-9]*\).*/\1/')"
          stmt="$(printf '%s' "$line" | sed 's/^## #[0-9]* *//' | tr '|' '/')"
          layers="" status="" ;;
        "layers: "*)    layers="$(printf '%s' "${line#layers: }" | tr '|' '/')" ;;
        "check_cmd: "*) status=checkable ;;
        "WITNESS:"*|"UNVERIFIABLE:"*) status=witness ;;
      esac
    done < "$run/CRITERIA.md"
    flush
  done
}

if [ "$MODE" = check ]; then
  [ -f "$INDEX" ] || { echo "criteria-index: --check but no $INDEX — build it first" >&2; exit 1; }
  want="$(emit)"
  if printf '%s\n' "$want" | diff -u "$INDEX" - >/dev/null 2>&1; then
    echo "criteria-index: in sync ($INDEX)"
    exit 0
  fi
  echo "criteria-index: DRIFT — $INDEX does not match the run corpus; rebuild with: criteria-index.sh --root <root>" >&2
  printf '%s\n' "$want" | diff -u "$INDEX" - | head -20 >&2
  exit 1
fi

emit > "$INDEX"
rows=$(grep -c '^| ' "$INDEX" || true)
echo "criteria-index: wrote $INDEX ($((rows>2 ? rows-2 : 0)) criteria indexed)"
