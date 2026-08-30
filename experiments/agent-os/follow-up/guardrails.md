# Compact safety guardrails

Keep desired design, observed live state, and runtime Evidence separate. A difference is a finding, not permission to rewrite either state. Name both states and the difference classification, propose separate design and live diffs, identify verification Evidence, and obtain explicit human approval before either diff is applied.

Each Adapter capability starts `unassessed`. An unprobed operation remains `unassessed`; use `unverified` only after that capability was probed or discovered but its evidence remained insufficient. Rate each capability independently as `native`, `partial`, `prose-only`, or `unsupported` only from current Adapter-specific evidence. Never infer support from prose, file presence, a harness name, or general reputation.
