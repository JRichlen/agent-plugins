---
id: scm.pull_request.read
kind: capability_interface
version: 1.0.0
effects: [network, scm:read]
---

# scm.pull_request.read

Read a pull request's metadata (title, body, state, refs) from a source-control
provider. Provider-independent: GitHub, GitLab, or a mock may implement it.
