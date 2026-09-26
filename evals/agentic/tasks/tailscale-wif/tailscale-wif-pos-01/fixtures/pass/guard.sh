#!/usr/bin/env bash
grep -q "id-token: write" workflow.yml && grep -q "oauth-client-id" workflow.yml && grep -q "audience" workflow.yml && ! grep -q "api-key" workflow.yml && ! grep -q "oauth-secret" workflow.yml && grep -q "vars.TS_OIDC" vars.md  # GUARD_CHECK
