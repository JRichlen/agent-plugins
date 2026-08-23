# AGENTS.md — egress-gate

Before any call that transmits repo or user content off-machine (posting a comment, pushing a branch, calling an external API with file contents in the payload), state what is being sent and to whom — permission modes gate the call, this gates the content. Use whenever output leaves the machine to a destination the user didn't name in this task.

## How to use it

Read `skills/egress-gate/SKILL.md` and follow it — it is the authoritative
description of this plugin's workflow and the invariant it defends.

The command `commands/egress-gate.md` is the entry point a user invokes.

## The invariant this plugin defends

Content leaving the machine is ALWAYS enumerated (what, to whom) before the transmitting call is made — and secrets, credentials, or content from outside the task's stated scope are NEVER included in an outbound payload.

The deterministic checks that defend it live in `evals/cheap/checks.sh` and run
as part of the marketplace cheap tier.
