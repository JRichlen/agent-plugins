# Shared check helpers for the cheap tier — sourced by BOTH evals/cheap/run.sh
# and evals/cheap/run-one.sh so the two runners cannot drift apart.
#
# WHY THIS FILE EXISTS (issue #120). run.sh defined six helpers; run-one.sh —
# the runner the REQUIRED install matrix uses — defined only three. Packs are
# sourced without `set -e`, so every call to a missing helper printed
# "command not found" on stderr and execution continued: run-one.sh reported
# "5 passed, 0 failed" over a pack containing 21 checks. 249 checks across 14
# plugins never ran in the required tier, and the ones dropped were
# disproportionately the invariant-verbatim assertions, because that is what
# has/hasE exist for.
#
# The runner that sources this must have already set: pass=0; fail=0
#
#   ok  MSG                   record a passing check
#   bad MSG                   record a failing check
#   group TITLE               print a section heading
#   has    FILE FIXED OK FAIL   fixed-string grep  (grep -qF)
#   hasE   FILE REGEX OK FAIL   regex grep         (grep -qE)
#   lacksE FILE REGEX OK FAIL   regex grep, inverted
ok()   { printf '  \033[32mPASS\033[0m %s\n' "$1"; pass=$((pass+1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=$((fail+1)); }
group(){ printf '\n\033[1m%s\033[0m\n' "$1"; }
has()   { if grep -qF "$2" "$1" 2>/dev/null; then ok "$3"; else bad "$4"; fi; }
hasE()  { if grep -qE "$2" "$1" 2>/dev/null; then ok "$3"; else bad "$4"; fi; }
lacksE(){ if grep -qE "$2" "$1" 2>/dev/null; then bad "$4"; else ok "$3"; fi; }

# Fail closed while a per-plugin pack is being sourced.
#
# Sourcing the helpers into both runners removes today's drift, but nothing
# stops tomorrow's: a pack calling a helper that no runner defines would again
# be a silent no-op. bash's command_not_found_handle turns that into a recorded
# FAILURE instead. It is installed ONLY around pack sourcing — a pack calling an
# unknown command is always a bug, whereas the generic sections legitimately
# probe for optional tools — and removed immediately after.
#
# Mechanism note, because the obvious version does not work: bash runs
# command_not_found_handle in a FORKED SUBSHELL, so a `bad` call inside it
# prints but its `fail=$((fail+1))` is lost when the child exits — the run would
# report the message and still exit 0. The handler therefore only RECORDS the
# missing command to a temp file, and pack_guard_off reads that file back in the
# parent shell and raises a real failure there.
pack_guard_on() {
  # Preserve any handler the environment already installed (several distros ship
  # one via a command-not-found package) so pack_guard_off can put it back
  # instead of clobbering it.
  _PACK_GUARD_PREV=""
  if declare -F command_not_found_handle >/dev/null 2>&1; then
    _PACK_GUARD_PREV="$(declare -f command_not_found_handle)"
  fi
  # Explicit template: bare `mktemp` is not portable to every platform. And if
  # it fails for any reason, say so as a FAILURE rather than continuing with an
  # empty path — a guard that quietly stops recording is the exact false-green
  # this whole change exists to remove.
  _PACK_GUARD_LOG="$(mktemp "${TMPDIR:-/tmp}/cheap-pack-guard.XXXXXX" 2>/dev/null || true)"
  if [ -z "$_PACK_GUARD_LOG" ] || [ ! -w "$_PACK_GUARD_LOG" ]; then
    _PACK_GUARD_LOG=""
    bad "pack guard could not create its record file — the fail-closed guard is UNAVAILABLE, so an undefined helper in this pack would go unrecorded (#120)"
    return 0
  fi
  command_not_found_handle() { printf '%s\n' "$1" >> "$_PACK_GUARD_LOG"; return 127; }
}
pack_guard_off() {
  unset -f command_not_found_handle 2>/dev/null || true
  # Restore the environment's own handler, if it had one.
  if [ -n "${_PACK_GUARD_PREV:-}" ]; then
    eval "$_PACK_GUARD_PREV"
  fi
  unset _PACK_GUARD_PREV
  if [ -n "${_PACK_GUARD_LOG:-}" ] && [ -s "$_PACK_GUARD_LOG" ]; then
    while IFS= read -r _cmd; do
      bad "pack called an undefined command '$_cmd' — a check that cannot run is not a check that passed (#120)"
    done < <(sort -u "$_PACK_GUARD_LOG")
  fi
  [ -n "${_PACK_GUARD_LOG:-}" ] && rm -f "$_PACK_GUARD_LOG"
  unset _PACK_GUARD_LOG
}
