# Hand off without copying the whole conversation

At a phase boundary, first decide whether another session is needed. The
[context-handoff skill](../../plugins/context-handoff/skills/context-handoff/SKILL.md)
checks continue, clear, handoff, delegate, then compact in that order. A progress
summary alone is not a reason to hand off.

For this stack, a real boundary is the implementation agent passing published
source to an independent documentation reviewer. The useful payload is the live
review task plus source pointers; the reviewer should read the actual diff,
not trust a copied description of it.

## A concise handoff shape

```text
Live thread: critique the newcomer path in this draft stack. Check whether a
new reader can complete the first task, find its undo and distinguish host
availability from actual qualification. Report concrete misses before edits.

Sources: the draft PR URLs and exact heads supplied with the review request;
docs/getting-started.md; docs/guides/; ci/README.md; release/README.md.
Open state: read each PR's current checks and evidence limits. No merge,
deployment, paid evaluation or global adoption is requested by this handoff.

Suggested methods: context-handoff on arrival; verify-before-claim before
reporting checks. Use actual source and the applicable host's available tools.
```

This is an instructional template for the real review boundary, not a claim
that another agent has already completed it. Before sending it, substitute the
actual PR URLs/heads and verify that every pointer resolves for the recipient.
Local paths alone do not travel to another machine.

## Verify the handoff

The sender checks resolvability, scans outbound content for secrets and states
what remains pending. The receiver reads those sources and attributes reported
results until independently checked. A supplied model name or writing style
does not prove authorship, independence or truth.

If the work still fits and no boundary needs crossing, continue in the same
session without producing another permanent status document. Keep decisions in
the existing issue, commit or PR; Git preserves prior states.
