---
id: scm.pull_request.comment
kind: capability_interface
version: 1.0.0
effects: [network, scm:write]
---

# scm.pull_request.comment

Post a comment on a pull request. Declares scm:write, so any agent compiled
under a read-only ceiling fails at link time if a selected module requires
this interface — the effect check is structural, not prose.
