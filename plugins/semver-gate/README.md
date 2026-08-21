# semver-gate

A judgment lens for agent autonomy, borrowed from semantic versioning. Every
pending action gets classified the way a code change would be classified
against a public API — **PATCH** (reversible, no observable contract change),
**MINOR** (additive, visible, non-breaking), or **MAJOR** (irreversible,
destroys or overwrites state, changes what's visible to others, or breaks a
contract someone else depends on) — and the classification sets the autonomy:

| Class | Autonomy |
|---|---|
| PATCH | Act silently. Mention it in the summary. No gate. |
| MINOR | Act, but flag it prominently; name the alternative if there's real ambiguity. Not a blocking question. |
| MAJOR | Stop. Never proceed on an assumption. Get explicit human sign-off for that specific action first. |

This is not a green-field autonomy policy — it's a precise vocabulary and a
concrete three-way mapping laid **on top of** judgment infrastructure that
likely already exists in your environment: a system-prompt instruction about
reversibility and blast radius, and (where configured) an `autoMode`
permission classifier with hardcoded verdicts for specific commands and repos.
Either of those always wins when they've already decided; this fills in the
cases they leave to unaided judgment. See `skills/semver-gate/SKILL.md` for
the exact semver.org and Conventional Commits language the mapping is
anchored to, a worked calibration example, and the decision procedure to run
in the moment.

## Install

```
/plugin marketplace add JRichlen/agent-plugins
/plugin install semver-gate@jrichlen
```

## Status

Real, not scaffolded. `evals/cheap/checks.sh` holds the skill's quoted spec
language, mapping table, and tie-break rule to exact substrings; the
behavioral tier in `evals/promptfoo/` checks that a model given the skill
actually stops for a MAJOR-class action, flags-but-acts on a MINOR-class one,
and doesn't gate on a PATCH-class one.

## License

MIT
