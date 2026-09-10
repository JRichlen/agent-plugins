#!/usr/bin/env bash
# Ephemeral GitHub runner provisioning only. Keep AppArmor and its global
# namespace restriction enabled; grant the bwrap executable its required
# namespace permission. See Ubuntu Noble's per-application userns policy.
set -euo pipefail
[[ "${GITHUB_ACTIONS:-}" == "true" ]] || {
  echo "bubblewrap provisioning is restricted to GitHub Actions runners" >&2
  exit 1
}
bwrap --version
if [[ "$(cat /sys/module/apparmor/parameters/enabled 2>/dev/null || true)" == "Y" ]] &&
   [[ "$(sysctl -n kernel.apparmor_restrict_unprivileged_userns 2>/dev/null || true)" == "1" ]]; then
  bwrap_profile_tmp="$(mktemp)"
  trap 'rm -f "$bwrap_profile_tmp"' EXIT
  cat > "$bwrap_profile_tmp" <<'PROFILE'
abi <abi/4.0>,
include <tunables/global>
profile agent_plugins_bwrap /usr/bin/bwrap flags=(unconfined) {
  userns,
}
PROFILE
  sudo install -m 0644 "$bwrap_profile_tmp" /etc/apparmor.d/agent-plugins-bwrap
  sudo apparmor_parser -r /etc/apparmor.d/agent-plugins-bwrap
fi
# A positive execution check must pass before any rejection can demonstrate
# isolation. An unavailable sandbox must not masquerade as a blocked attack.
python3 -m unittest \
  evals.agentic.tests.test_grader_forgery.GraderForgery.test_correct_originals_still_pass -v
