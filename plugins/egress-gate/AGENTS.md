# egress-gate repository entry point

Load [the authoritative method](skills/egress-gate/SKILL.md) before applying this
plugin. Its entry conditions, action boundaries, procedure and exit live there;
this discovery file does not maintain a second policy copy. Follow its links to
references only as needed. The user entry point is
[the command](commands/egress-gate.md).

Run the package's `evals/cheap/checks.sh` through the repository cheap runner
when changing it; see [testing](../../docs/testing.md) for additional checks and
host limitations.
