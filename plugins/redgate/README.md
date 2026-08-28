# redgate

Run any idea through Red Gate: rounds of ARM/TRACE/JUDGE with graduated autonomy — each round gate is classified PATCH/MINOR/MAJOR via semver-gate, so derived work auto-passes inside a human-approved mandate while scout decisions, plan approval, and irreversible actions always block on the human. ARM emits a verifier proven able to fail; JUDGE is that pinned verifier run by a party that did not do the work. Use on /redgate "<idea>", or whenever done-criteria must be proven falsifiable before building.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install redgate@jrichlen
```

## Install with APM (Codex / Copilot / any harness)

APM's `marketplace_plugin` resolver reads this marketplace's manifest
directly:

```sh
apm install JRichlen/agent-plugins/plugins/redgate        # unpinned (main)
apm install JRichlen/agent-plugins/plugins/redgate#<sha>  # reproducible
apm compile -t copilot   # aggregates into .github/copilot-instructions.md
```

Codex reads the plugin's `AGENTS.md` natively; Claude Code installs it as a
plugin via the marketplace. The scripts are plain bash and run identically
under all three.

## Status

All five slices (per `docs/red-gate-implementation-plan.md` at the marketplace
root): driver + ARM, with the red gate live and executed by the cheap
tier's dogfood check — a fresh scaffold's `check.sh` must exit red, harness
failure must be 99, a 127 must be a FAIL, and pinning must record both
sha256s. An optional hooks enforcement layer (Claude-Code-only;
on another harness the same rules apply as prose discipline), and the
protocol references are the next slices.

## License

MIT
