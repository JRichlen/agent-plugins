#!/usr/bin/env bash
! grep -qi retry .redgate/notify-service/artifacts/notify.py && grep -qi widen .redgate/notify-service/gates.log  # GUARD_CHECK
