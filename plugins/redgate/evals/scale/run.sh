#!/usr/bin/env bash
#
# Scale/stress tier for redgate — the cheap tier proves each gate once, on one
# fixture; this suite proves the SAME gates hold across many randomized,
# isolated runs, so a defect that only shows up on a particular criteria count,
# a partially-green contract, or a particular mutation order cannot hide behind
# a single lucky fixture.
#
# Per randomized run (in its own temp dir, seeded and reproducible):
#   red-from-birth   a fresh scaffold's check.sh exits 1, with evidence written
#   custom contract  3-7 randomized criteria, all red, evidence per criterion
#   unpinned refused reconcile before --pin is refused outright
#   pin              manifest gains two 64-hex sha256s, phase flips to TRACE;
#                    a second --pin is refused
#   unmet != drift   a pinned run with unmet criteria reads unmet, never drift
#   partial progress satisfying a random strict subset still reads unmet
#   green            satisfying every criterion: check.sh exits 0 AND
#                    reconcile exits 0 (proven, evidence-fresh)
#   drift (criteria) mutating CRITERIA.md post-pin fails reconcile, exit-coupled
#   drift (checker)  mutating check.sh post-pin fails reconcile, exit-coupled
#   stale evidence   RG_TEST_DROP_EVIDENCE=1 fails a passing run (freshness gate)
#   guard            the PreToolUse guard handler (a plain stdin/stdout filter,
#                    runnable on any harness) denies CRITERIA.md / check.sh /
#                    manifest edits mid-TRACE (exit 2), allows the same edits in
#                    ARM, and allows unrelated paths (exit 0)
#
# Offline, isolated, no network. Not part of the cheap tier (it takes tens of
# seconds, not milliseconds); CI runs it via .github/workflows/scale.yml.
#
#   RUNS=50 plugins/redgate/evals/scale/run.sh    # more runs
#   plugins/redgate/evals/scale/run.sh            # default 25
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN="$(cd "$HERE/../.." && pwd)"
SCAF="$PLUGIN/skills/criteria-contract/scripts/scaffold-run.sh"
RECON="$PLUGIN/skills/reconcile/scripts/reconcile.sh"
GUARD="$PLUGIN/hooks/hooks-handlers/guard-redgate-paths.sh"

RUNS="${RUNS:-25}"
SEED="${SEED:-4242}"
RANDOM=$SEED

pass=0; failn=0
ok()  { pass=$((pass+1)); }
bad() { failn=$((failn+1)); echo "  FAIL $*"; }

payload() { printf '{"tool_name":"Edit","tool_input":{"file_path":"%s"}}' "$1"; }

for r in $(seq 1 "$RUNS"); do
  d="$(mktemp -d)"; slug="s$r"; run="$d/.redgate/$slug"; art="$d/artifacts"
  mkdir -p "$art"

  # -- scaffold + red-from-birth on the template contract ---------------------
  "$SCAF" --slug "$slug" --root "$d" >/dev/null 2>&1 \
    || { bad "run $r: scaffold failed"; rm -rf "$d"; continue; }
  bash "$run/check.sh" >/dev/null 2>&1; rc=$?
  [ "$rc" -eq 1 ] && ok || bad "run $r: fresh scaffold check.sh rc=$rc (want 1: red from birth)"

  # -- randomized contract: 3-7 criteria, every one red today -----------------
  n=$((3 + RANDOM % 5))
  : > "$run/CRITERIA.md"
  for i in $(seq 1 "$n"); do
    printf '## #%d artifact %d exists\nlayers: fs\nred-because: absent\ncheck_cmd: test -f %s/%s-%d.txt\n\n' \
      "$i" "$i" "$art" "$slug" "$i" >> "$run/CRITERIA.md"
  done
  bash "$run/check.sh" >/dev/null 2>&1; rc=$?
  [ "$rc" -eq 1 ] && ok || bad "run $r: custom contract not red (rc=$rc, n=$n)"
  miss=0
  for i in $(seq 1 "$n"); do [ -f "$run/evidence/$i.out" ] || miss=$((miss+1)); done
  [ "$miss" -eq 0 ] && ok || bad "run $r: $miss/$n criteria wrote no evidence"

  # -- unpinned reconcile is refused ------------------------------------------
  out="$("$RECON" --slug "$slug" --root "$d" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'not pinned\|unpinned'; then ok
  else bad "run $r: unpinned run was graded (rc=$rc)"; fi

  # -- pin: two sha256s, phase=TRACE; re-pin refused --------------------------
  "$SCAF" --pin "$slug" --root "$d" >/dev/null 2>&1 \
    || { bad "run $r: pin failed"; rm -rf "$d"; continue; }
  shas="$(grep -cE '(criteria|check)_sha256=[0-9a-f]{64}' "$run/manifest")"
  [ "$shas" -eq 2 ] && ok || bad "run $r: pin wrote $shas/2 sha256s"
  grep -q 'phase=TRACE' "$run/manifest" && ok || bad "run $r: pin did not flip phase to TRACE"
  if "$SCAF" --pin "$slug" --root "$d" >/dev/null 2>&1; then
    bad "run $r: RE-pin was accepted"
  else ok; fi

  # -- unmet reads unmet, never drift -----------------------------------------
  out="$("$RECON" --slug "$slug" --root "$d" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'unmet' \
     && ! printf '%s' "$out" | grep -qi 'drift'; then ok
  else bad "run $r: all-unmet run misreported (rc=$rc)"; fi

  # -- partial progress (random strict subset green) is still unmet -----------
  if [ "$n" -gt 1 ]; then
    k=$((1 + RANDOM % (n - 1)))
    for i in $(seq 1 "$k"); do : > "$art/$slug-$i.txt"; done
    out="$("$RECON" --slug "$slug" --root "$d" 2>&1)"; rc=$?
    if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'unmet'; then ok
    else bad "run $r: partially-green run ($k/$n) did not read unmet (rc=$rc)"; fi
  fi

  # -- full green: check.sh 0, reconcile 0 -------------------------------------
  for i in $(seq 1 "$n"); do : > "$art/$slug-$i.txt"; done
  bash "$run/check.sh" >/dev/null 2>&1; rc=$?
  [ "$rc" -eq 0 ] && ok || bad "run $r: all-satisfied check.sh rc=$rc (want 0)"
  "$RECON" --slug "$slug" --root "$d" >/dev/null 2>&1; rc=$?
  [ "$rc" -eq 0 ] && ok || bad "run $r: green run failed reconcile (rc=$rc)"

  # -- mutations, each on a fresh copy of the green run ------------------------
  c="$d.copy1"; cp -R "$d" "$c"
  printf '\n## #%d smuggled\nlayers: x\nred-because: n/a\ncheck_cmd: true\n' "$((n+1))" \
    >> "$c/.redgate/$slug/CRITERIA.md"
  out="$("$RECON" --slug "$slug" --root "$c" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'CRITERIA drift'; then ok
  else bad "run $r: criteria tamper not caught as drift (rc=$rc)"; fi
  rm -rf "$c"

  c="$d.copy2"; cp -R "$d" "$c"
  echo '# tampered' >> "$c/.redgate/$slug/check.sh"
  out="$("$RECON" --slug "$slug" --root "$c" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'CHECKER drift'; then ok
  else bad "run $r: checker tamper not caught as drift (rc=$rc)"; fi
  rm -rf "$c"

  out="$(RG_TEST_DROP_EVIDENCE=1 "$RECON" --slug "$slug" --root "$d" 2>&1)"; rc=$?
  if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qi 'evidence'; then ok
  else bad "run $r: stale evidence was accepted (rc=$rc)"; fi

  # -- guard handler: deny pinned-contract edits mid-TRACE, allow the rest -----
  for f in CRITERIA.md check.sh manifest; do
    payload "$run/$f" | bash "$GUARD" >/dev/null 2>&1; rc=$?
    [ "$rc" -eq 2 ] && ok || bad "run $r: guard rc=$rc for TRACE $f (want 2: deny)"
  done
  payload "$run/NOTES.md" | bash "$GUARD" >/dev/null 2>&1; rc=$?
  [ "$rc" -eq 0 ] && ok || bad "run $r: guard denied a non-contract file in the run dir (rc=$rc)"
  payload "$d/src/other.ts" | bash "$GUARD" >/dev/null 2>&1; rc=$?
  [ "$rc" -eq 0 ] && ok || bad "run $r: guard denied a path outside .redgate (rc=$rc)"

  arm="$(mktemp -d)"
  "$SCAF" --slug arm --root "$arm" >/dev/null 2>&1
  payload "$arm/.redgate/arm/CRITERIA.md" | bash "$GUARD" >/dev/null 2>&1; rc=$?
  [ "$rc" -eq 0 ] && ok || bad "run $r: guard denied an ARM-phase (pre-pin) contract edit (rc=$rc)"
  rm -rf "$arm" "$d"
done

echo
echo "redgate scale: $RUNS randomized runs (seed=$SEED), $pass assertions passed, $failn failed"
[ "$failn" -eq 0 ] || exit 1
