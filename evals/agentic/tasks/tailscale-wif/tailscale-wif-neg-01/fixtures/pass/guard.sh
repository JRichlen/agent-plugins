#!/usr/bin/env bash
grep -q "gitops-acl-action@newsha456" workflow.yml && grep -q "oauth-client-id" workflow.yml  # GUARD_CHECK
