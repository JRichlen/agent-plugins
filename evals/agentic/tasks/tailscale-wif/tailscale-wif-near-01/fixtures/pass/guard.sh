#!/usr/bin/env bash
grep -q "oauth-client-id" workflow.yml && ! grep -q "oauth-secret" workflow.yml  # GUARD_CHECK
