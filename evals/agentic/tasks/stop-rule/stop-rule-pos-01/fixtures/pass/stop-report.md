objective: fix the flaky CI check
attempt 1: pushed fix A -- still red (literal: assertion mismatch line 12)
attempt 2: pushed fix B -- still red (literal: timeout after 30s)
attempt 3: pushed fix C -- still red (literal: assertion mismatch line 12, again)
hypothesis 1: fix A/C target the wrong assertion -- check by reading the assertion source
hypothesis 2: the timeout in attempt 2 was an unrelated flake -- check by rerunning in isolation
