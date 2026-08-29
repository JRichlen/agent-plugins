#!/usr/bin/env bash
#
# gate-report.sh — the per-class gate-outcome report with approval-fatigue
# detection (gap #9, docs/research/gap-analysis.md).
#
# Usage: gate-report.sh [--root DIR]
#
# Graduated autonomy is the marketplace's differentiating idea, and until now
# it had no feedback loop on whether MAJOR asks get genuine attention — the one
# signal deciding whether the model works or quietly trains rubber-stamping.
# This reads every .redgate/*/gates.log, tallies gates per class, breaks down
# the recorded human dispositions, and flags the fatigue shapes worth a look.
#
# Dispositions (the gates.log column, see the redgate driver's gate ledger):
#   auto     — PATCH auto-pass, no human involved
#   silent   — MINOR flagged; the standing veto was not exercised
#   vetoed   — MINOR veto exercised
#   approved — MAJOR: the human said yes as asked
#   revised  — MAJOR: the human changed the ask before approving
#   declined — MAJOR: the human said no
# Lines from ledgers predating the column are counted as `unrecorded` — the
# report says so out loud rather than inventing a disposition.
#
# This is a READER for humans and for recurrence-detector's gather step: it
# always exits 0 on a readable corpus (warnings are findings, not failures);
# 2 on usage or when no gates.log exists at all.
set -uo pipefail

ROOT="$PWD"
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:?}"; shift 2 ;;
    *) echo "usage: gate-report.sh [--root DIR]" >&2; exit 2 ;;
  esac
done

logs="$(ls "$ROOT"/.redgate/*/gates.log 2>/dev/null | sort)"
[ -n "$logs" ] || { echo "gate-report: no gates.log under $ROOT/.redgate/*/ — nothing to report" >&2; exit 2; }

# shellcheck disable=SC2086
awk -F'|' '
function trim(s){ gsub(/^[ \t]+|[ \t]+$/, "", s); return s }
/^[ \t]*#/ { next }                       # ledger header comments
NF < 2     { next }
{
  cls = trim($2)
  if (cls != "PATCH" && cls != "MINOR" && cls != "MAJOR") { legacy++; next }
  total[cls]++
  grand++
  # Disposition column: 6-field lines are round|class|driving|disposition|outcome|lesson.
  # Older 4/5-field ledgers predate the column — count those as unrecorded.
  d = (NF >= 6) ? trim($4) : ""
  if (d != "auto" && d != "silent" && d != "vetoed" && d != "approved" && d != "revised" && d != "declined") d = "unrecorded"
  disp[cls, d]++
  if (d == "unrecorded") unrec++
}
END {
  if (grand == 0) { print "gate-report: ledgers found but no PATCH/MINOR/MAJOR gate lines"; exit 0 }
  print "gate-report: per-class gate outcomes (" grand " gates, " NR " ledger lines)"
  print "---"
  split("PATCH MINOR MAJOR", order, " ")
  split("auto silent vetoed approved revised declined unrecorded", ds, " ")
  for (i = 1; i <= 3; i++) {
    c = order[i]
    if (!(c in total)) continue
    line = sprintf("  %-5s %3d gates:", c, total[c])
    for (j in ds) if ((c, ds[j]) in disp) line = line sprintf("  %s=%d", ds[j], disp[c, ds[j]])
    print line
  }
  if (legacy) print "  (plus " legacy " non-gate ledger lines: stage markers, legacy END rows)"
  print "---"
  warned = 0
  # Fatigue shape 1: every MAJOR sails through unchanged. Either the mandate is
  # perfectly calibrated or approval has become a reflex — sample the last few.
  m = total["MAJOR"] + 0
  ma = disp["MAJOR", "approved"] + 0
  if (m >= 5 && ma == m) {
    print "  WARNING approval-fatigue: all " m " MAJOR gates approved as asked, zero revised/declined."
    print "          A mandate this frictionless is either perfectly calibrated or rubber-stamped —"
    print "          re-read the last 5 MAJOR entries and check the questions were real."
    warned++
  }
  # Fatigue shape 2: the MINOR standing veto has never once been exercised.
  n = total["MINOR"] + 0
  if (n >= 5 && disp["MINOR", "vetoed"] + 0 == 0) {
    print "  NOTE  the MINOR standing veto has never been exercised across " n " gates —"
    print "        confirm the prominent flag is actually being seen, not scrolled past."
    warned++
  }
  # Fatigue shape 3: the ledger is not capturing dispositions at all.
  if (unrec + 0 > grand / 2) {
    print "  NOTE  " unrec "/" grand " gates have no recorded disposition (ledgers predate the"
    print "        column, or entries omit it) — the fatigue signals above are underpowered."
    warned++
  }
  if (!warned) print "  no fatigue shapes flagged"
}
' $logs
