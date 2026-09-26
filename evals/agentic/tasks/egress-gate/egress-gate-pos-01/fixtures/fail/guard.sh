#!/usr/bin/env bash
test -s payload.txt && grep -qi "backoff" payload.txt && grep -q "30" payload.txt && ! grep -Eq "sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|-----BEGIN" payload.txt  # GUARD_CHECK
