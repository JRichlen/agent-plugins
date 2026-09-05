group "jori — manifest and shipped surface"
manifest="$PLUGIN_DIR/.claude-plugin/plugin.json"
skill="$PLUGIN_DIR/skills/jori/SKILL.md"
[ -f "$manifest" ] && ok "Claude manifest exists" || bad "Claude manifest missing"
[ -f "$skill" ] && ok "skill entrypoint exists" || bad "skill entrypoint missing"
if python3 - "$manifest" <<'PY'
import json, sys
p = json.load(open(sys.argv[1]))
assert p["name"] == "jori"
assert p["version"] == "0.0.1"
assert p["skills"] == "./skills/"
assert p["commands"] == "./commands/"
print("ok - Claude manifest schema and wiring")
PY
then
  ok "Claude manifest schema and wiring"
else
  bad "Claude manifest schema or wiring is invalid"
fi
grep -q "allow_implicit_invocation: true" "$PLUGIN_DIR/skills/jori/agents/openai.yaml" && ok "implicit invocation enabled" || bad "implicit invocation metadata missing"
for path in "$PLUGIN_DIR/skills/jori/references/orchestration.md" "$PLUGIN_DIR/skills/jori/assets/dashboard-template.md" "$PLUGIN_DIR/context/AGENTS.fragment.md" "$PLUGIN_DIR/commands/jori.md"; do
  [ -f "$path" ] && ok "resource exists: ${path##*/}" || bad "resource missing: $path"
done
if grep -R -n -E "TODO|/mnt/c/Users|SCAFFOLD-UNIMPLEMENTED" "$PLUGIN_DIR/skills" "$PLUGIN_DIR/context" "$PLUGIN_DIR/AGENTS.md" "$PLUGIN_DIR/README.md" "$PLUGIN_DIR/commands" >/dev/null; then
  bad "portable package contains TODO, scaffold sentinel, or personal path"
else
  scan_status=$?
  if [ "$scan_status" -eq 1 ]; then
    ok "portable package has no scaffold placeholders or personal paths"
  else
    bad "portable package placeholder scan could not complete"
  fi
fi

group "jori — coordination invariant is load-bearing"
# These phrases live in the operative SKILL.md, not in a summary or this pack.
# They make the central claims falsifiable at the free tier: delegation is real
# and bounded, authority does not silently expand, and status is evidence-based.
for rule in \
  "delegates substantive work through bounded real agents" \
  "preserves user authority over deep or wide changes" \
  "never claims work or monitoring that did not happen" \
  "Workers do not interview the user or expand authority" \
  "Ask the user before materially widening, deepening, increasing cost" \
  "Simple work gets no dashboard or ceremony"; do
  if grep -Fq "$rule" "$skill"; then
    ok "skill keeps: $rule"
  else
    bad "skill dropped coordination rule: $rule"
  fi
done
