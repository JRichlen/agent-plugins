#!/usr/bin/env bash
#
# scaffold-run.sh — create (or pin) a Red Gate run under .redgate/<slug>/.
#
# Create:  scaffold-run.sh --slug <slug> [--root DIR] [--rounds N]
# Pin:     scaffold-run.sh --pin <slug> [--root DIR]
#
# Create emits: CRITERIA.md (template), check.sh (harness), evidence/,
# manifest (phase=BEGIN, budgets, empty pins). The template criteria are
# honestly red: their check_cmds probe artifacts that do not exist yet, so a
# freshly scaffolded run's check.sh exits 1 (red) — never 0 — until real
# criteria replace the template AND real work flips them.
#
# Pin records sha256 of BOTH CRITERIA.md and check.sh into the manifest and
# flips phase to MIDDLE. After pinning, neither file is ever edited: END
# re-hashes both, and a mismatch fails the run as drift.
#
# Exit codes: 0 ok; 2 usage / refused (existing run, missing run, already
# pinned); no other codes are emitted by this generator itself.
set -euo pipefail

usage() { sed -n '3,8p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

MODE="" SLUG="" ROOT="$PWD" ROUNDS=4
while [ $# -gt 0 ]; do
  case "$1" in
    --slug)   MODE=create; SLUG="${2:?}"; shift 2 ;;
    --pin)    MODE=pin;    SLUG="${2:?}"; shift 2 ;;
    --root)   ROOT="${2:?}"; shift 2 ;;
    --rounds) ROUNDS="${2:?}"; shift 2 ;;
    *) usage ;;
  esac
done
[ -n "$MODE" ] && [ -n "$SLUG" ] || usage
case "$SLUG" in (*[!a-z0-9-]*|"") echo "slug must be kebab-case" >&2; exit 2 ;; esac

RUN="$ROOT/.redgate/$SLUG"

if [ "$MODE" = pin ]; then
  [ -f "$RUN/manifest" ] || { echo "no run at $RUN" >&2; exit 2; }
  grep -q '^criteria_sha256=$' "$RUN/manifest" || { echo "already pinned; a pinned contract is never re-pinned" >&2; exit 2; }
  CS=$(sha256sum "$RUN/CRITERIA.md" | cut -d' ' -f1)
  KS=$(sha256sum "$RUN/check.sh"    | cut -d' ' -f1)
  # in-place field fill; manifest keys are fixed at create time
  sed -i "s/^criteria_sha256=$/criteria_sha256=$CS/" "$RUN/manifest"
  sed -i "s/^check_sha256=$/check_sha256=$KS/"       "$RUN/manifest"
  sed -i "s/^phase=BEGIN$/phase=MIDDLE/"             "$RUN/manifest"
  echo "pinned: criteria=$CS check=$KS phase=MIDDLE"
  exit 0
fi

[ -e "$RUN" ] && { echo "refusing to clobber existing run at $RUN" >&2; exit 2; }
mkdir -p "$RUN/evidence"

cat > "$RUN/manifest" <<EOF
slug=$SLUG
phase=BEGIN
round=1
round_budget=$ROUNDS
depth_remaining=2
attempts_per_criterion=2
autonomy=classified
approved_plan_sha256=
criteria_sha256=
check_sha256=
EOF

# The gate ledger: every round-gate decision appends one line here —
# round | gate class (PATCH/MINOR/MAJOR) | driving property | outcome.
# An auto-pass that cannot cite its qualifying conditions is a protocol
# violation; MAJOR decisions record the human's answer, never a default.
printf '# gates.log — round | class | driving-property | outcome\n' > "$RUN/gates.log"

cat > "$RUN/CRITERIA.md" <<'EOF'
# CRITERIA — replace every TEMPLATE block, keep the numbering

<!-- Each criterion: statement, layers it crosses, why it is red today
     (absent | present-but-wrong), and a check_cmd — or UNVERIFIABLE with a
     named human observation (max 1 without explicit human opt-in).
     At least two criteria must be checkable; checkable must be the majority.
     After ratification this file is NEVER edited. -->

## #1 TEMPLATE — the primary behavior this round exists to produce
layers: TEMPLATE
red-because: absent — the artifact does not exist yet
check_cmd: test -f artifacts/TEMPLATE-primary-output

## #2 TEMPLATE — the seam-proving behavior (no stub at this seam)
layers: TEMPLATE
red-because: absent — nothing produces this yet
check_cmd: grep -q TEMPLATE-proof artifacts/TEMPLATE-primary-output
EOF

cat > "$RUN/check.sh" <<'CHECKEOF'
#!/usr/bin/env bash
# Red Gate verifier harness. Exit: 0 all checkable green; 1 any FAIL (red);
# 99 harness failure (preflight dirty / internal error) — 99 is NOT red.
# Each check_cmd runs under timeout, stdin closed, output teed to
# evidence/<n>.out. A check_cmd exiting non-zero for ANY reason (127
# included) is a FAIL — only the harness's own breakage is exit 99.
set -u
cd "$(dirname "$0")"

# ---- preflight: HARNESS prerequisites only; never the subject under test ----
for bin in bash timeout tee sha256sum grep sed; do
  command -v "$bin" >/dev/null 2>&1 || { echo "HARNESS-ERROR: missing $bin" >&2; exit 99; }
done
[ -d evidence ] && [ -w evidence ] || { echo "HARNESS-ERROR: evidence/ not writable" >&2; exit 99; }
[ -f CRITERIA.md ] || { echo "HARNESS-ERROR: CRITERIA.md missing" >&2; exit 99; }

fails=0; checked=0
n=0
while IFS= read -r line; do
  case "$line" in
    "## #"*) n=$(printf '%s' "$line" | sed 's/^## #\([0-9]*\).*/\1/') ;;
    "check_cmd: "*)
      cmd=${line#check_cmd: }
      checked=$((checked+1))
      if timeout 120 bash -c "$cmd" </dev/null >"evidence/$n.out" 2>&1; then
        echo "#$n PASS"
      else
        echo "#$n FAIL"; fails=$((fails+1))
      fi ;;
    "UNVERIFIABLE:"*) echo "#$n UNVERIFIABLE" ;;
  esac
done < CRITERIA.md

[ "$checked" -gt 0 ] || { echo "HARNESS-ERROR: no checkable criteria parsed" >&2; exit 99; }
[ "$fails" -eq 0 ] && exit 0 || exit 1
CHECKEOF
chmod +x "$RUN/check.sh"

echo "scaffolded $RUN (phase=BEGIN, round_budget=$ROUNDS)"
echo "next: replace the TEMPLATE criteria, run check.sh (must be red), ratify, then: $0 --pin $SLUG${ROOT:+ --root $ROOT}"
