# Offline source-contract and mutation controls for bounded delegated execution.
# These checks defend the operative procedure; they do not measure model benefit.
if python3 "$PLUGIN_DIR/evals/cheap/check_contract.py" "$PLUGIN_DIR"; then
  ok "delegated execution contract and templates are complete"
else
  bad "delegated execution contract or templates are incomplete"
fi
if python3 "$PLUGIN_DIR/evals/cheap/check_contract.py" "$PLUGIN_DIR" --self-test; then
  ok "delegated execution rejects deleted clauses and retired policy"
else
  bad "delegated execution mutation controls failed"
fi
