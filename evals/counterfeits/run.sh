#!/usr/bin/env bash
#
# Counterfeit corpus — the meta-test that proves the cheap tier is not a rubber stamp.
#
# The cheap tier (evals/cheap/run.sh) asserts that GOOD plugins pass. That is only
# half of a real gate. A gate that never rejected anything would also pass every
# good plugin — so "green on the real repo" tells us nothing about whether the gate
# actually DISCRIMINATES. This runner supplies the missing half: a corpus of
# deliberately broken plugins, each of which the cheap tier MUST reject, and reject
# for the RIGHT reason.
#
# How it stays safe to keep in the repo: the broken artifacts are never stored on
# disk. We keep ONE all-valid baseline plugin (evals/counterfeits/baseline/) that is
# invisible to the real tier (it lives under evals/, not plugins/), and each fixture
# ships a mutate.sh that breaks a COPY at runtime inside a temp dir. Nothing broken
# ever persists, so the always-on cheap tier stays green.
#
# For each fixture we:
#   1. build a synthetic marketplace root (copy evals/cheap + baseline plugins +
#      baseline marketplace.json into a temp dir),
#   2. run the COPIED run.sh once to confirm the baseline is GREEN — this is the
#      calibration step: if a "known-good" plugin fails, the corpus is miscalibrated
#      and every rejection below is meaningless,
#   3. apply the fixture's mutate.sh to a fresh copy,
#   4. run the copied run.sh and assert it exits NON-ZERO *and* prints the fixture's
#      EXPECT_FAIL_SUBSTRING — proving the RIGHT gate fired, not just any failure.
#
# Exit 0 = baseline green AND every counterfeit rejected by its expected gate.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
BASELINE="$HERE/baseline"
FIXTURES="$HERE/fixtures"

pass=0; fail=0
ok()   { printf '  \033[32mPASS\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=$((fail+1)); }
group(){ printf '\n\033[1m%s\033[0m\n' "$1"; }

# Assemble a synthetic marketplace root that the COPIED run.sh will scan. The
# copied run.sh computes REPO_ROOT as its own ../.. — i.e. the temp root — so it
# lints exactly the tree we build here and nothing from the real repo.
build_root() {
  local root; root="$(mktemp -d)"
  mkdir -p "$root/evals" "$root/.claude-plugin"
  cp -R "$REPO_ROOT/evals/cheap" "$root/evals/cheap"
  cp -R "$BASELINE/plugins" "$root/plugins"
  cp "$BASELINE/.claude-plugin/marketplace.json" "$root/.claude-plugin/marketplace.json"
  # Stage the REPO-LEVEL gate inputs so the branch-protection lock (§11), the
  # paid-pack discovery self-test (§11b) and the install-smoke coverage gate (§12)
  # actually FIRE in the synthetic root instead of being silently inert for lack of
  # their inputs. The real (in-sync/valid) copies keep the baseline green; fixtures
  # 12-14 mutate them to prove each gate bites.
  mkdir -p "$root/.github/workflows" "$root/ci"
  cp "$REPO_ROOT/.github/workflows/evals.yml" "$root/.github/workflows/evals.yml"
  cp -R "$REPO_ROOT/ci/." "$root/ci/"
  cp -R "$REPO_ROOT/evals/paid" "$root/evals/paid"
  # Stage a top-level README.md (§5b is guarded on its presence, same as the
  # gates above) so "README documents every registered plugin" fires here too;
  # fixture 16 mutates it to prove the gate bites.
  cp "$BASELINE/README.md" "$root/README.md"
  printf '%s' "$root"
}

run_tier() {  # <root> -> prints combined output, returns run.sh exit code
  "$1/evals/cheap/run.sh" 2>&1
}

# --- calibration: the baseline must be GREEN --------------------------------
# If the known-good plugin doesn't pass the real gate, the corpus proves nothing:
# a rejection could just mean the baseline itself is broken. Assert green first.
group "calibration — baseline plugin passes the cheap tier"
cal_root="$(build_root)"
if cal_out="$(run_tier "$cal_root")"; then
  ok "baseline plugin is green (gate discriminates from a known-good starting point)"
else
  bad "baseline plugin is NOT green — corpus is miscalibrated, every rejection below is meaningless"
  printf '%s\n' "$cal_out" | sed 's/^/    /'
fi
rm -rf "$cal_root"

# --- coverage: the repo-level gates must FIRE in the synthetic root ----------
# §11/§11b/§12 are inert unless build_root stages their inputs. If it ever stops,
# the gate's group header vanishes from the baseline run and its fixture(s) below
# would silently pass by never triggering — this catches that coverage regression
# (the "add a gate but leave it unexercised" drift the corpus exists to prevent).
group "gate coverage — repo-level gates fire in the synthetic root"
for g in "branch-protection lock" "paid-pack discovery self-test" "install-smoke coverage" "README documents every registered plugin"; do
  if grep -qF "$g" <<<"$cal_out"; then ok "gate fires in synthetic root: $g"; else bad "gate '$g' did NOT fire in the synthetic root — build_root staging regressed"; fi
done

# --- each counterfeit must be rejected by its expected gate -----------------
group "counterfeits — each broken plugin is rejected for the right reason"
for dir in "$FIXTURES"/*/; do
  name="$(basename "$dir")"
  defect="$dir/DEFECT.md"
  mutate="$dir/mutate.sh"
  if [ ! -f "$defect" ] || [ ! -f "$mutate" ]; then
    bad "$name is missing DEFECT.md or mutate.sh"; continue
  fi
  expect="$(sed -n 's/^EXPECT_FAIL_SUBSTRING=//p' "$defect" | head -n1)"
  if [ -z "$expect" ]; then
    bad "$name DEFECT.md has no EXPECT_FAIL_SUBSTRING= line"; continue
  fi

  root="$(build_root)"
  if ! bash "$mutate" "$root" >/dev/null 2>&1; then
    bad "$name mutate.sh failed to apply"; rm -rf "$root"; continue
  fi

  out="$(run_tier "$root")"; code=$?
  if [ "$code" -eq 0 ]; then
    bad "$name was ACCEPTED by the cheap tier (expected rejection: '$expect')"
  elif ! grep -qF "$expect" <<<"$out"; then
    bad "$name rejected, but not by the expected gate (missing '$expect')"
    printf '%s\n' "$out" | grep -i fail | sed 's/^/    /'
  else
    ok "$name rejected by the expected gate ('$expect')"
  fi
  rm -rf "$root"
done

# --- summary ----------------------------------------------------------------
printf '\n\033[1msummary:\033[0m %d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
