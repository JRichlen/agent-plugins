---
description: >-
  Before any call that transmits repo or user content off-machine (posting a comment, pushing a branch, calling an external API with file contents in the payload), state what is being sent and to whom — permission modes gate the call, this gates the content. Use whenever output leaves the machine to a destination the user didn't name in this task.
---

Invoke the `egress-gate` skill and follow `skills/egress-gate/SKILL.md`.

For the outbound call about to happen (or the one the user described): write
the egress manifest first — what is in the payload, by name, and the concrete
destination — then sweep the payload for secrets, credentials, personal data
beyond need, and out-of-scope content, blocking the call until any hit is
removed. If the destination wasn't named by the user in this task, turn the
manifest into a question and wait rather than send.
