# Cheap eval pack for the 'agent-compiler' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group and $PLUGIN_NAME / $PLUGIN_DIR.
#
# This pack EXECUTES the kernel and asserts the plugin invariant on real
# output — golden, metamorphic, and fail-closed — rather than grepping for
# sentences about it. Offline, stdlib-python + bash, sub-second.

group "plugin 'agent-compiler': kernel scripts compile"
_ac_dir="$PLUGIN_DIR"
_ac_py="python3"
if $_ac_py -m py_compile "$_ac_dir/scripts/compile.py" 2>/dev/null; then
  ok "scripts/compile.py compiles (py_compile)"
else
  bad "scripts/compile.py fails py_compile"
fi
if $_ac_py -m py_compile "$_ac_dir/scripts/render_claude_agent.py" 2>/dev/null; then
  ok "scripts/render_claude_agent.py compiles (py_compile)"
else
  bad "scripts/render_claude_agent.py fails py_compile"
fi

_ac_reg="$_ac_dir/registry"
_ac_query="$_ac_dir/examples/queries/security-pr-review.json"
_ac_golden="$_ac_dir/examples/golden/security-pr-review.image.json"
_ac_tmp="$(mktemp -d)"

group "plugin 'agent-compiler': golden — byte-identical, deterministic, order-independent"
if $_ac_py "$_ac_dir/scripts/compile.py" compile --registry "$_ac_reg" \
    --query "$_ac_query" > "$_ac_tmp/run1.json" 2>/dev/null; then
  ok "golden query compiles"
else
  bad "golden query failed to compile"
fi
if [ -f "$_ac_golden" ] && cmp -s "$_ac_tmp/run1.json" "$_ac_golden"; then
  ok "compiled image is byte-identical to the committed golden image"
else
  bad "compiled image differs from examples/golden/security-pr-review.image.json — regenerate the golden ONLY for an intended behavior change"
fi
$_ac_py "$_ac_dir/scripts/compile.py" compile --registry "$_ac_reg" \
  --query "$_ac_query" > "$_ac_tmp/run2.json" 2>/dev/null
if cmp -s "$_ac_tmp/run1.json" "$_ac_tmp/run2.json"; then
  ok "repeated compilation is byte-identical"
else
  bad "repeated compilation produced different bytes — determinism broken"
fi
$_ac_py "$_ac_dir/scripts/compile.py" compile --registry "$_ac_reg" \
  --query "$_ac_query" --discovery-order reverse > "$_ac_tmp/rev.json" 2>/dev/null
if cmp -s "$_ac_tmp/run1.json" "$_ac_tmp/rev.json"; then
  ok "reversed file-discovery order yields byte-identical output"
else
  bad "file-discovery order changed the output — canonical ordering broken"
fi

group "plugin 'agent-compiler': metamorphic — unrelated module leaves the image hash unchanged"
cp -r "$_ac_reg" "$_ac_tmp/reg-unrelated"
cp "$_ac_dir/evals/cheap/fixtures/unrelated.md" "$_ac_tmp/reg-unrelated/"
_ac_h1="$($_ac_py -c "import json;print(json.load(open('$_ac_tmp/run1.json'))['hash'])")"
_ac_h2="$($_ac_py "$_ac_dir/scripts/compile.py" compile --registry "$_ac_tmp/reg-unrelated" \
  --query "$_ac_query" 2>/dev/null | $_ac_py -c "import json,sys;print(json.load(sys.stdin)['hash'])")"
if [ -n "$_ac_h1" ] && [ "$_ac_h1" = "$_ac_h2" ]; then
  ok "adding an unrelated module does not change the image hash"
else
  bad "unrelated module changed the image hash ($_ac_h1 vs $_ac_h2)"
fi

group "plugin 'agent-compiler': fail-closed — each violation dies with its diagnostic code"
# _ac_expect_fail NAME EXPECTED_CODE FIXTURE...  (overlays fixtures onto a
# registry copy; compile must exit nonzero AND emit the expected code)
_ac_expect_fail() {
  local name="$1" code="$2"; shift 2
  local d="$_ac_tmp/reg-$name"
  rm -rf "$d"; cp -r "$_ac_reg" "$d"
  local f; for f in "$@"; do cp "$f" "$d/"; done
  local out rc
  out="$($_ac_py "$_ac_dir/scripts/compile.py" compile --registry "$d" --query "$_ac_query" 2>/dev/null)"; rc=$?
  if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -qF "\"code\":\"$code\""; then
    ok "$name fails compilation with $code"
  else
    bad "$name did NOT fail with $code (exit=$rc) — fail-closed clause broken"
  fi
}
_ac_fx="$_ac_dir/evals/cheap/fixtures"
_ac_expect_fail conflict     CONFLICT           "$_ac_fx/conflict.md"
_ac_expect_fail missing-dep  MISSING_DEPENDENCY "$_ac_fx/missing-dep.md"
_ac_expect_fail cycle        DEPENDENCY_CYCLE   "$_ac_fx/cycle-a.md" "$_ac_fx/cycle-b.md"
_ac_expect_fail over-ceiling EFFECT_CEILING     "$_ac_fx/over-ceiling.md"
# read-only agents never link write effects — same clause, asserted on the image
if grep -qF 'scm:write' "$_ac_tmp/run1.json"; then
  bad "golden image links a write effect under a read-only ceiling"
else
  ok "golden (read-only) image links no write effect"
fi
# no ceiling anywhere -> refuse, never fail open
_ac_nc_out="$($_ac_py "$_ac_dir/scripts/compile.py" compile --registry "$_ac_reg" \
  --query "$_ac_fx/no-ceiling-query.json" 2>/dev/null)"
if [ $? -ne 0 ] && printf '%s' "$_ac_nc_out" | grep -qF '"code":"NO_EFFECT_CEILING"'; then
  ok "a query with no effect ceiling anywhere is refused (NO_EFFECT_CEILING)"
else
  bad "ceiling-less compile did not fail closed with NO_EFFECT_CEILING"
fi

group "plugin 'agent-compiler': provenance on every emitted unit"
if $_ac_py - "$_ac_tmp/run1.json" <<'PY'
import json, sys
img = json.load(open(sys.argv[1]))
units = img.get("behavior", [])
assert units, "image emitted no behavior units"
for u in units:
    p = u.get("provenance") or {}
    assert p.get("module") and p.get("source") and p.get("version"), \
        f"unit {u.get('id')} lacks provenance"
PY
then
  ok "every emitted behavior unit carries module/source/version provenance"
else
  bad "a behavior unit was emitted without provenance"
fi

rm -rf "$_ac_tmp"
