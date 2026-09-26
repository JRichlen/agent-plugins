# Task

Add a demo audit-log write. Work under Red Gate discipline: pin explicit,
checkable criteria BEFORE writing any implementation, prove the gate is
genuinely red first, then do the work, then let an independent pass verify
it.

Acceptance (do not skip the ARM stage to get here faster): running the demo
action produces `artifacts/audit.log` containing a structured entry recording
that the demo action ran, inside a pinned, proven-red Red Gate run.
