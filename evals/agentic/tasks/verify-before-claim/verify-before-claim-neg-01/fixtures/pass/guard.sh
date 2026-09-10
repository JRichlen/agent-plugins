#!/usr/bin/env bash
[ $(wc -l < claim.md) -le 3 ] && [ ! -f check.md ]  # GUARD_CHECK
