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
if $_ac_py -m py_compile "$_ac_dir/scripts/mcp_server.py" 2>/dev/null; then
  ok "scripts/mcp_server.py compiles (py_compile)"
else
  bad "scripts/mcp_server.py fails py_compile"
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
_ac_expect_fail typo-key     BAD_MODULE_KEY     "$_ac_fx/typo-key.md"
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

group "plugin 'agent-compiler': identities, applicability, stance"
_ac_eq="$_ac_dir/examples/queries/engineering-default.json"
_ac_eg="$_ac_dir/examples/golden/engineering-default.image.json"
if $_ac_py "$_ac_dir/scripts/compile.py" compile --registry "$_ac_reg" \
    --query "$_ac_eq" > "$_ac_tmp/eng.json" 2>/dev/null \
    && [ -f "$_ac_eg" ] && cmp -s "$_ac_tmp/eng.json" "$_ac_eg"; then
  ok "engineering-default identity compiles byte-identical to its golden"
else
  bad "engineering-default identity drifted from examples/golden/engineering-default.image.json"
fi
# applicability: prove-the-undo declares risks:[high,critical]; the medium-risk
# golden must NOT carry it, and raising risk to high must pull it in.
if grep -qF 'discipline.prove-the-undo' "$_ac_tmp/eng.json"; then
  bad "risk-gated module leaked into a medium-risk compile (applicability broken)"
else
  ok "risk-gated module (prove-the-undo) excluded at risk=medium"
fi
$_ac_py - "$_ac_eq" > "$_ac_tmp/eng-high.query.json" <<'PY'
import json, sys
q = json.load(open(sys.argv[1])); q["risk"] = "high"
print(json.dumps(q))
PY
if $_ac_py "$_ac_dir/scripts/compile.py" compile --registry "$_ac_reg" \
    --query "$_ac_tmp/eng-high.query.json" 2>/dev/null | grep -qF 'discipline.prove-the-undo'; then
  ok "risk-gated module (prove-the-undo) selected at risk=high"
else
  bad "risk=high did not select the risk-gated module (applicability broken)"
fi
# stance must be declared by a selected view — fail closed otherwise
_ac_st_out="$($_ac_py "$_ac_dir/scripts/compile.py" compile --registry "$_ac_reg" \
  --query "$_ac_dir/evals/cheap/fixtures/bad-stance-query.json" 2>/dev/null)"
if [ $? -ne 0 ] && printf '%s' "$_ac_st_out" | grep -qF '"code":"UNDECLARED_STANCE"'; then
  ok "undeclared stance is refused (UNDECLARED_STANCE)"
else
  bad "a stance no view declares compiled anyway — stance validation broken"
fi

group "plugin 'agent-compiler': hooks — guard compiled artifacts, suggest the compiler"
if $_ac_py -m py_compile "$_ac_dir/hooks/guard-compiled-agents.py" \
    && $_ac_py -m py_compile "$_ac_dir/hooks/suggest-compiler.py"; then
  ok "hook scripts compile (py_compile)"
else
  bad "a hook script fails py_compile"
fi
if $_ac_py -c "import json; json.load(open('$_ac_dir/hooks/hooks.json'))" 2>/dev/null; then
  ok "hooks/hooks.json is valid JSON"
else
  bad "hooks/hooks.json missing or invalid"
fi
$_ac_py "$_ac_dir/scripts/render_claude_agent.py" \
  --image "$_ac_golden" --out "$_ac_tmp/compiled-agent.md" 2>/dev/null
_ac_deny="$(printf '%s' "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$_ac_tmp/compiled-agent.md\"}}" \
  | $_ac_py "$_ac_dir/hooks/guard-compiled-agents.py")"
if printf '%s' "$_ac_deny" | grep -qF '"permissionDecision": "deny"'; then
  ok "guard hook denies hand-edits of a compiled artifact"
else
  bad "guard hook did NOT deny a hand-edit of a compiled artifact"
fi
_ac_medeny="$(printf '%s' "{\"tool_name\":\"MultiEdit\",\"tool_input\":{\"file_path\":\"$_ac_tmp/compiled-agent.md\",\"edits\":[{\"old_string\":\"a\",\"new_string\":\"b\"}]}}" \
  | $_ac_py "$_ac_dir/hooks/guard-compiled-agents.py")"
if printf '%s' "$_ac_medeny" | grep -qF '"permissionDecision": "deny"'; then
  ok "guard hook denies a MultiEdit of a compiled artifact"
else
  bad "MultiEdit bypassed the compiled-artifact guard"
fi
_ac_mldeny="$(printf '%s' "{\"tool_name\":\"MultiEdit\",\"tool_input\":{\"edits\":[{\"file_path\":\"$_ac_dir/README.md\"},{\"file_path\":\"$_ac_tmp/compiled-agent.md\"}]}}" \
  | $_ac_py "$_ac_dir/hooks/guard-compiled-agents.py")"
if printf '%s' "$_ac_mldeny" | grep -qF '"permissionDecision": "deny"'; then
  ok "guard hook denies a multi-target edit whose second path is compiled"
else
  bad "a compiled artifact hidden in a multi-target edit list bypassed the guard"
fi
_ac_allow="$(printf '%s' "{\"tool_name\":\"Edit\",\"tool_input\":{\"file_path\":\"$_ac_dir/README.md\"}}" \
  | $_ac_py "$_ac_dir/hooks/guard-compiled-agents.py")"
if [ -z "$_ac_allow" ]; then
  ok "guard hook stays silent for ordinary files"
else
  bad "guard hook produced output for an ordinary file (over-blocking)"
fi
_ac_ctx="$(printf '%s' '{"prompt":"make me a security reviewer agent for this repo"}' \
  | $_ac_py "$_ac_dir/hooks/suggest-compiler.py")"
if printf '%s' "$_ac_ctx" | grep -qF '"additionalContext"' \
    && printf '%s' "$_ac_ctx" | grep -qF 'compile'; then
  ok "suggest hook injects compiler context on agent-building intent"
else
  bad "suggest hook did not fire on agent-building intent"
fi
_ac_quiet="$(printf '%s' '{"prompt":"run the agent tests and fix the failing one"}' \
  | $_ac_py "$_ac_dir/hooks/suggest-compiler.py")"
if [ -z "$_ac_quiet" ]; then
  ok "suggest hook stays silent on ordinary prompts"
else
  bad "suggest hook fired on an ordinary prompt (noise)"
fi
if printf 'not json' | $_ac_py "$_ac_dir/hooks/guard-compiled-agents.py" >/dev/null 2>&1 \
    && printf 'not json' | $_ac_py "$_ac_dir/hooks/suggest-compiler.py" >/dev/null 2>&1; then
  ok "both hooks fail open on malformed stdin (exit 0)"
else
  bad "a hook errored on malformed stdin — a broken hook must never block work"
fi

group "plugin 'agent-compiler': MCP facade — same kernel, same guarantees, over stdio"
if $_ac_py - "$_ac_dir" "$_ac_golden" <<'PY'
import json, os, subprocess, sys
plugin, golden_path = sys.argv[1], sys.argv[2]
proc = subprocess.Popen(
    [sys.executable, os.path.join(plugin, "scripts", "mcp_server.py")],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
def rpc(method, params=None, msg_id=None):
    m = {"jsonrpc": "2.0", "method": method}
    if msg_id is not None: m["id"] = msg_id
    if params is not None: m["params"] = params
    proc.stdin.write(json.dumps(m) + "\n"); proc.stdin.flush()
    return json.loads(proc.stdout.readline()) if msg_id is not None else None
init = rpc("initialize", {"protocolVersion": "2025-06-18",
                          "clientInfo": {"name": "eval", "version": "0"},
                          "capabilities": {}}, 1)
assert init["result"]["serverInfo"]["name"] == "agent-compiler", "bad serverInfo"
rpc("notifications/initialized")
tools = {t["name"] for t in rpc("tools/list", None, 2)["result"]["tools"]}
assert tools == {"inspect", "compile", "explain", "render"}, f"tool set drifted: {tools}"
query = json.load(open(os.path.join(plugin, "examples/queries/security-pr-review.json")))
r = rpc("tools/call", {"name": "compile", "arguments": {"query": query}}, 3)
assert not r["result"]["isError"], "golden compile errored via MCP"
image = json.loads(r["result"]["content"][0]["text"])
golden = json.load(open(golden_path))
assert image["hash"] == golden["hash"], "MCP compile hash differs from golden"
bad_q = {k: v for k, v in query.items() if k not in ("effectCeiling", "stance")}
bad_q["views"] = []
r = rpc("tools/call", {"name": "compile", "arguments": {"query": bad_q}}, 4)
assert r["result"]["isError"], "ceiling-less compile did not error via MCP"
codes = {d["code"] for d in json.loads(r["result"]["content"][0]["text"])["diagnostics"]}
assert "NO_EFFECT_CEILING" in codes, f"wrong codes via MCP: {codes}"
proc.stdin.close(); proc.wait(timeout=5)
assert proc.returncode == 0, "server did not exit cleanly"
PY
then
  ok "MCP stdio round-trip: handshake, tool set, golden hash via compile, fail-closed via facade"
else
  bad "MCP facade round-trip failed — facade drifted from the kernel's guarantees"
fi

rm -rf "$_ac_tmp"
