#!/usr/bin/env bash
grep -q 'phase=TRACE' .redgate/user-criteria/manifest && test -f .redgate/user-criteria/evidence/ARM_RED_PROOF.txt  # GUARD_CHECK
