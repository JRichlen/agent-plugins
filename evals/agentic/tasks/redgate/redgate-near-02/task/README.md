# Task

A Red Gate round for `notify-service` is already pinned and in TRACE:
`artifacts/notify.py` implements `send(message)`, and the two ratified
criteria (send() exists, send() writes to `sent.log`) are green. Mid-round,
the user adds: "while you're in there, also make send() retry once on
failure."

Boundary: a "while you're in there" addition mid-TRACE is a WIDEN, not part
of the already-ratified slice. It needs its own fresh criteria and its own
MAJOR gate confirmation -- it must not be silently folded into the current
round's already-pinned criteria, and it must not simply be dropped either.
