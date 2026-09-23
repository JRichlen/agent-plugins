#!/usr/bin/env bash
#
# redact-vendor-ids.sh — strip account identifiers out of vendor error text
# before it reaches a PUBLIC CI log. Reads stdin, writes stdout.
#
# WHY
#
# OpenRouter's 402 and 429 bodies are genuinely useful for diagnosis — they name
# the affordable max_tokens, they carry `limit_source`, they quote the vendor's
# own remedy — so the eval jobs echo them, and should. But they also embed
# account identifiers that no part of the diagnosis needs:
#
#   * a workspace key-management URL whose last path segment is the KEY'S ID,
#     e.g. https://openrouter.ai/workspaces/default/keys/<64 hex>
#   * a `user_id`, e.g. user_3DoPG2oto9Ch95XfcoyYBjZiXn1
#
# None of that is the API key itself, so the severity is low. But a public
# Actions log is permanent and indexable once archived, and this repo's own
# `egress-gate` plugin exists to make exactly this kind of leak a decision
# rather than an accident. Cheap to strip, so strip it.
#
# WHAT IS DELIBERATELY KEPT
#
# Everything that explains the failure: the HTTP code, the message text, the
# token figures, `limit_source`, `provider_name`, `remedy_hint`. Redaction that
# eats the diagnosis would just move the problem — the whole reason these bodies
# are printed is that a blank error box cost this repo two runs and two wrong
# public diagnoses (PR #131).
#
# USAGE
#
#   redact-vendor-ids.sh < body.json
#   some-jq-program ... | redact-vendor-ids.sh
#
# Single-sourced on purpose: it is called from evals/paid/check-subject-model.sh
# and from three separate failing-transcript dumps in .github/workflows/evals.yml
# (behavioral, routing, trajectory). A fourth echo site that forgets to pipe
# through it is what the cheap tier's guard looks for.
set -uo pipefail

sed -E \
  -e 's#(openrouter\.ai/workspaces/)[^ "]*#\1<redacted>#g' \
  -e 's/[0-9a-f]{32,}/<redacted-id>/g' \
  -e 's/user_[A-Za-z0-9]{8,}/user_<redacted>/g'
