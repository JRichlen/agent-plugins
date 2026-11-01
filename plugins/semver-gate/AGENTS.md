# semver-gate repository entry point

Load [the authoritative method](skills/semver-gate/SKILL.md) before applying this
plugin. Its entry conditions, action boundaries, procedure and exit live there;
this discovery file does not maintain a second policy copy. Follow its links to
references only as needed. The user entry point is
[the command](commands/semver-gate.md).

For the restoration rehearsal, also load
[prove-the-undo](skills/prove-the-undo/SKILL.md) and its
[command](commands/prove-the-undo.md). The classification skill owns when it is required.

Run the package's `evals/cheap/checks.sh` through the repository cheap runner
when changing it; see [testing](../../docs/testing.md) for additional checks and
host limitations.
