---
name: egress-gate
description: >-
  Before any call that transmits repo or user content off-machine (posting
  a comment, pushing a branch, calling an external API with file contents
  in the payload), state what is being sent and to whom — permission modes
  gate the call, this gates the content. Use whenever output leaves the
  machine to a destination the user didn't name in this task.
license: MIT
compatibility: >-
  PORTABILITY: pure pre-transmission discipline — no hooks, no
  subagent-spawning tool, no Workflow tool, no harness-specific primitive.
  The manifest is a sentence written before the transmitting call, whatever
  that call is in the local harness (a git push, an API tool, an MCP call).
  Ports to any harness whose agent can describe a payload before sending it.
---

# egress-gate

## Invariant

Content leaving the machine is ALWAYS enumerated (what, to whom) before the
transmitting call is made — and secrets, credentials, or content from
outside the task's stated scope are NEVER included in an outbound payload.

## Not this

- **Harness permission modes** (allowlists, `autoMode` patterns, per-tool
  prompts) gate *which calls* may run, by tool and pattern. They cannot see
  that an allowed call carries the wrong *content* — a permitted
  `git push` with a `.env` accidentally staged, a permitted issue-comment
  tool posting an internal hostname. egress-gate covers exactly that gap:
  the payload of an already-permitted call. Where a permission rule blocks
  a call outright, that rule wins; this skill never argues a blocked call
  back open.

- **semver-gate** (`plugins/semver-gate`) classifies risk and decides
  whether to ask. Transmission is often MINOR by its table (visible,
  revertible-ish) — but even a PATCH/MINOR transmission still owes the
  egress manifest, because the manifest is about content enumeration, not
  permission to act. On MAJOR, both apply.

- **scope-fence** (`plugins/scope-fence`) bounds what the *diff* contains;
  egress-gate bounds what a *payload* contains. Its "task's stated scope"
  clause borrows the same fence: content unrelated to the task doesn't
  belong in an outbound payload any more than in the diff.

## When to use this

Immediately before any call whose effect is content leaving the machine:
pushing a branch, opening a PR, posting an issue/PR/Slack comment, uploading
an artifact, calling an external API with file contents, logs, or
conversation excerpts in the payload, or publishing anything. The gate
applies with extra force when the destination was not named by the user in
this task — sending a diff to the repo the user pointed you at is expected;
sending an excerpt to an analytics or search API they never mentioned is
exactly the case this exists for.

## The gate

1. **Enumerate before transmitting.** In the turn where the transmitting
   call happens, before it, state the egress manifest: *what* is in the
   payload (files, ranges, generated text — by name, not "the changes") and
   *to whom* it goes (the concrete destination: repo and branch, issue URL,
   API host). One or two sentences; a payload too complicated to enumerate
   is too complicated to send.

2. **Sweep the payload for what never leaves.** Secrets and credentials
   (keys, tokens, `.env` contents, connection strings), personal data
   beyond what the task requires, and content from outside the task's
   stated scope (unrelated files that snuck into staging, conversation
   context the destination has no need of). Finding any of these blocks
   the call until the payload is cleaned — there is no "it's probably
   fine" branch.

3. **Unnamed destination → ask first.** If the destination was not named by
   the user in this task and is not the obvious home of the work, the
   manifest becomes a question rather than an announcement: say what would
   be sent and where, and wait. Sending is publishing; it may be cached or
   indexed even if deleted later.

## Failure modes this exists to stop

- A staged `.env` riding inside a permitted `git push`.
- An error report pasted to an external service with an internal hostname
  or token still in the traceback.
- File contents sent to a third-party API the user never mentioned, because
  the tool was available and allowed.
- "The push was permitted" standing in for "the payload was checked."
