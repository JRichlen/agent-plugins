# Cheap eval pack for the 'stop-rule' plugin — SOURCED by evals/cheap/run.sh
# with cwd = repo root; inherits ok/bad/group/has/hasE/lacksE and
# $PLUGIN_NAME / $PLUGIN_DIR.
#
# What this defends: a bound declared up front, honest per-objective counting,
# and a mandatory stop-and-report at the bound — never attempt N+1 on momentum.

group "stop-rule — structure"
ok "stop-rule structure"

group "stop-rule — invariant survives verbatim"
ok "stop-rule invariant"
