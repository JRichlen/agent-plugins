# `fixtures/native/usage/` — hand-authored usage records

Backlog T30 is explicit that these are **hand-authored against documented field
names**, and **not** claimed to be recorded CLI output. No recorded transcript
exists in this repository, and producing one is an approval-gated native run
(§10.6) — so a fixture worded "recorded from the installed CLIs" would smuggle
an approval-gated action into an unapproved evidence class.

Every file carries a `PROVENANCE` key naming where the shape came from and
flagging what the source does not pin down. An approved capture would *upgrade*
these fixtures; T30's closure does not depend on it, which is why T30 stays
`real-fixture` and `approval_gate: none`.
