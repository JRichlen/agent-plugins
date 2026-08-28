#!/usr/bin/env bash
#
# secret-gate.sh FILE... — mechanical secret scan over agent-written exhaust.
#
# Agent-written exhaust (redgate gates.log files, dev-diary drafts, handoff
# artifacts) is exactly the surface where a pasted credential slips into a
# committed file: the prose around it looks routine, so no human WITNESS reads
# it closely before it travels off-machine. This gate is the mechanical WITNESS
# instead — dependency-free (plain grep -E, nothing to install), so it can run
# in the cheap tier and in any harness a skill hands it to. It is deliberately
# a floor, not a ceiling: the mandate is "obvious token shapes never ship",
# not "all secrets are detectable by regex". UPGRADE PATH: when a real scanner
# is acceptable as a dependency, replace the pattern table below with gitleaks
# or trufflehog and keep this file's CLI contract (exit codes, allowlist).
#
# Exit contract (COUPLED to the negative control in evals/cheap/run.sh):
#   0 = every scanned file clean
#   1 = at least one hit; each hit printed as "HIT <file>:<line> (<label>)"
#       (file+line+label only — never echo the matched secret itself)
#   2 = usage error / named file missing
#
# Internal allowlist — two exemptions, both because they carry the patterns
# ON PURPOSE and would otherwise make the gate flag its own machinery:
#   * this script itself (the pattern table below contains literal matches,
#     e.g. the private-key header and the sk-ant- prefix)
#   * any path containing /fixtures/ (eval fixtures deliberately hold FAKE
#     secrets — e.g. evals/cheap/fixtures/secret-gate/leaky.txt — so the
#     always-on tier stays green while the negative control scans a COPY of
#     the fixture staged outside /fixtures/ to prove the teeth are real)
set -uo pipefail

self="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

if [ "$#" -eq 0 ]; then
  echo "usage: secret-gate.sh FILE..." >&2
  exit 2
fi

# label<TAB>ERE pairs. Every pattern is anchored to a distinctive PREFIX or
# literal header, never a bare entropy guess, so false positives stay near
# zero on prose. (Heredoc is quoted: nothing here is expanded by the shell.)
patterns="$(cat <<'EOF'
aws-access-key-id	AKIA[0-9A-Z]{16}
github-token	(ghp|gho|ghs)_[A-Za-z0-9]{20,}
github-fine-grained-pat	github_pat_[A-Za-z0-9_]{20,}
slack-token	xox[baprs]-[A-Za-z0-9-]{10,}
generic-api-key	[Aa][Pp][Ii][_-]?[Kk][Ee][Yy][[:space:]]*[:=][[:space:]]*["']?[A-Za-z0-9_/+.=-]{20,}
private-key-header	-----BEGIN [A-Z ]*PRIVATE KEY-----
anthropic-api-key	sk-ant-[A-Za-z0-9_-]{8,}
EOF
)"

hits=0
for f in "$@"; do
  if [ ! -f "$f" ]; then
    echo "secret-gate: no such file: $f" >&2
    exit 2
  fi
  # Resolve to an absolute path so the allowlist matches regardless of how the
  # caller spelled the path (relative, ./-prefixed, symlinked cwd).
  abs="$(cd "$(dirname "$f")" && pwd)/$(basename "$f")"
  case "$abs" in
    "$self")      continue ;;  # own source: pattern table is literal bait
    */fixtures/*) continue ;;  # eval fixtures: fake secrets by design
  esac
  while IFS=$'\t' read -r label rx; do
    [ -z "$label" ] && continue
    # Print file+line+label per hit — the LOCATION, never the secret itself,
    # since this gate's own output may land in logs that also travel.
    while IFS= read -r ln; do
      [ -z "$ln" ] && continue
      printf 'HIT %s:%s (%s)\n' "$f" "$ln" "$label"
      hits=$((hits+1))
    done < <(grep -nE "$rx" "$f" 2>/dev/null | cut -d: -f1)
  done <<< "$patterns"
done

if [ "$hits" -eq 0 ]; then
  echo "secret-gate: clean ($# file(s) scanned)"
  exit 0
fi
echo "secret-gate: $hits hit(s) — remove or redact before this exhaust travels" >&2
exit 1
