# Deliverable interface

Stage `plugin.json`, `marketplace-entry.json`, `checks.sh`, and `invariant.md` for `demo-widget`. The plugin manifest has `name: demo-widget` and a `version` of three numeric components separated by periods. The marketplace entry has the same name and `source: ./plugins/demo-widget`. State these metadata validity requirements as a concrete failure condition in the invariant.

`bash checks.sh DIRECTORY` must validate the two JSON files in that directory: exit zero for valid metadata (including other valid numeric versions), and nonzero for a missing/malformed plugin manifest, an incorrect name in either file, an invalid version, or an incorrect marketplace source. The check must have working success and failure paths. Do not publish or install the staged plugin.
