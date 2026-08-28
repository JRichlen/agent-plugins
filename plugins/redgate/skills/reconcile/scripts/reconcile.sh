#!/usr/bin/env bash
#
# reconcile.sh — the JUDGE stage of a Red Gate round — the independent verdict.
#
# Usage: reconcile.sh --slug <slug> [--root DIR]
#
# Run this from a context that did NOT do the work: a fresh subagent, a fresh
# session, or the human. It is handed only the criteria, the checker, and the
# diff — never the build transcript.
#
# It refuses to grade a run that was never ratified, fails the run outright if
# either pinned artifact drifted, runs the pinned verifier itself, and accepts
# a PASS only when the harness wrote evidence for it during THIS run.
#
# Exit: 0 all checkable criteria green and proven; 1 a criterion is not green,
# or drift/evidence rejection fails the run; 2 usage / unpinned / missing run.
#
# RG_TEST_DROP_EVIDENCE=1 deletes evidence after the verifier runs — the
# negative control that proves the freshness gate can actually fail.
set -uo pipefail

usage() { sed -n '3,6p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

SLUG="" ROOT="$PWD"
while [ $# -gt 0 ]; do
  case "$1" in
    --slug) SLUG="${2:?}"; shift 2 ;;
    --root) ROOT="${2:?}"; shift 2 ;;
    *) usage ;;
  esac
done
[ -n "$SLUG" ] || usage

RUN="$ROOT/.redgate/$SLUG"
[ -f "$RUN/manifest" ] || { echo "reconcile: no run at $RUN" >&2; exit 2; }

field() { sed -n "s/^$1=//p" "$RUN/manifest" | head -1; }

# ---- 1. ratification gate -------------------------------------------------
# An unpinned run was never ratified. There is no contract to grade against,
# and grading one would let a writer author criteria after seeing results.
PIN_C="$(field criteria_sha256)"
PIN_K="$(field check_sha256)"
if [ -z "$PIN_C" ] || [ -z "$PIN_K" ]; then
  echo "reconcile: run '$SLUG' is not pinned (unpinned run — never ratified); refusing to verify" >&2
  exit 2
fi

# ---- 2. drift gate --------------------------------------------------------
# Either pinned artifact changing after ratification fails the run outright.
NOW_C="$(sha256sum "$RUN/CRITERIA.md" | cut -d' ' -f1)"
NOW_K="$(sha256sum "$RUN/check.sh"    | cut -d' ' -f1)"
drift=0
[ "$NOW_C" = "$PIN_C" ] || { echo "reconcile: CRITERIA drift — pinned $PIN_C, found $NOW_C" >&2; drift=1; }
[ "$NOW_K" = "$PIN_K" ] || { echo "reconcile: CHECKER drift — pinned $PIN_K, found $NOW_K" >&2; drift=1; }
if [ "$drift" -ne 0 ]; then
  echo "reconcile: VERDICT FAIL (criteria drift) — a ratified artifact was edited after pinning" >&2
  exit 1
fi

# ---- 3. run the pinned verifier ourselves ---------------------------------
START=$(date +%s)
sleep 1                      # ensure evidence mtimes are strictly newer than START
VERDICTS="$(bash "$RUN/check.sh" 2>&1)"; VRC=$?
if [ "$VRC" -eq 99 ]; then
  echo "reconcile: FAULT (exit 99) — not a verdict; fix the harness" >&2
  printf '%s\n' "$VERDICTS" >&2
  exit 1
fi

[ "${RG_TEST_DROP_EVIDENCE:-0}" = "1" ] && rm -f "$RUN"/evidence/*.out

# ---- 4. evidence gate + verdict table -------------------------------------
# A PASS is accepted only when the harness wrote evidence for it during this
# run. A verdict with missing or stale evidence is rejected, never trusted.
fails=0; unproven=0; green=0
echo "reconcile: run=$SLUG  round=$(field round)  criteria=$PIN_C"
echo "---"
while IFS= read -r line; do
  case "$line" in
    "#"*) : ;;
    *) continue ;;
  esac
  n="${line#\#}"; n="${n%% *}"
  verdict="${line##* }"
  ev="$RUN/evidence/$n.out"
  case "$verdict" in
    PASS)
      if [ ! -f "$ev" ]; then
        printf '#%s\tREJECTED\tPASS claimed, evidence file missing (%s)\n' "$n" "evidence/$n.out"
        unproven=$((unproven+1))
      elif [ "$(stat -c %Y "$ev" 2>/dev/null || echo 0)" -lt "$START" ]; then
        printf '#%s\tREJECTED\tPASS claimed, evidence stale (older than this run)\n' "$n"
        unproven=$((unproven+1))
      else
        printf '#%s\tPASS\tevidence/%s.out\n' "$n" "$n"
        green=$((green+1))
      fi ;;
    FAIL)
      printf '#%s\tFAIL\tevidence/%s.out\n' "$n" "$n"; fails=$((fails+1)) ;;
    WITNESS|UNVERIFIABLE)
      printf '#%s\tWITNESS\tdeclared at ARM; human observation required\n' "$n" ;;
  esac
done <<< "$VERDICTS"
echo "---"

if [ "$unproven" -gt 0 ]; then
  echo "reconcile: VERDICT FAIL — $unproven criterion/criteria claimed PASS without fresh evidence" >&2
  exit 1
fi
if [ "$fails" -gt 0 ]; then
  echo "reconcile: VERDICT FAIL — $fails unmet; next smallest slice: take the lowest-numbered FAIL and flip only that"
  exit 1
fi
echo "reconcile: VERDICT PASS — $green criteria green, each with evidence written this run"
echo "reconcile: mutation control — revert the slice's core hunk and re-run; a criterion still green is WITNESS-in-fact, not proven"
exit 0
