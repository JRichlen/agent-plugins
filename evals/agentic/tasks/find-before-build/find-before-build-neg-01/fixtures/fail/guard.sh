#!/usr/bin/env bash
test -f scratch/explore.py && grep -q 'def ' scratch/explore.py && [ ! -f RECEIPT.md ]  # GUARD_CHECK
