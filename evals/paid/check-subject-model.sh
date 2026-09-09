#!/usr/bin/env bash
#
# check-subject-model.sh — confirm the model every behavioral pack actually
# TESTS is callable right now.
#
# CI has always confirmed the Anthropic grader slug resolves and never once
# checked the OpenRouter subject. A revoked key, an exhausted balance or a moved
# slug therefore produces packs where every real-skill row fails, with no signal
# anywhere — which is how two refresh runs (2026-09-01, 2026-09-08) graded all
# 12 packs, spent ~50 minutes of paid API time, captured nothing, and reported
# success.
#
# It lives in a script rather than inline in a workflow because BOTH the evals
# workflow and the refresh workflow must run it — the refresh is the one that
# actually spends the budget, so preflighting only the former would leave the
# expensive path unguarded (caught in review of PR #131).
#
# Provider ids are read from the parsed YAML `providers:` list, never grepped
# out of the file: a commented-out historical slug left above the active one
# during a migration would otherwise be picked up and reported green while
# promptfoo called a different, broken model (also caught in that review).
#
# Fails closed. Every step that could yield nothing is asserted, and the run
# refuses to exit 0 unless it actually pinged at least one model.
#
# Usage:
#   check-subject-model.sh           # ping every distinct subject slug
#   check-subject-model.sh --list    # print the slugs it WOULD ping; no network
#
# Env: OPENROUTER_API_KEY (required unless --list)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT" || exit 1

MODE="${1:-ping}"
case "$MODE" in
  --list) MODE=list ;;
  ping|"") MODE=ping ;;
  *) echo "usage: check-subject-model.sh [--list]" >&2; exit 2 ;;
esac

if ! plugins="$(evals/paid/discover-paid-packs.sh promptfoo)"; then
  echo "::error::discover-paid-packs.sh failed — cannot tell which packs exist, so nothing was verified." >&2
  exit 1
fi
if [ "$plugins" = "[]" ]; then
  echo "no promptfoo packs — nothing to resolve"
  exit 0
fi
if ! names="$(printf '%s' "$plugins" | jq -r '.[]' 2>/dev/null)" || [ -z "$names" ]; then
  echo "::error::could not parse the discovered pack list as JSON — nothing was verified." >&2
  printf '%s\n' "$plugins" | head -5 >&2
  exit 1
fi

# Extract every ACTIVE openrouter provider id from each pack's parsed YAML.
subjects="$(python3 - $names <<'PY'
import os, sys
sys.dont_write_bytecode = True
def ids_from(cfg):
    """Active provider ids only. Parse the YAML; a commented-out slug is not a
    provider and must never be returned."""
    try:
        import yaml
        doc = yaml.safe_load(open(cfg)) or {}
        out = []
        for p in (doc.get("providers") or []):
            pid = p.get("id") if isinstance(p, dict) else p
            if isinstance(pid, str):
                out.append(pid)
        return out
    except ImportError:
        pass
    except Exception as e:
        print(f"PARSE-ERROR {cfg}: {e}", file=sys.stderr)
        return None
    # PyYAML absent: walk the providers block by hand, skipping comment lines.
    out, in_block = [], False
    for line in open(cfg):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if not in_block:
            if line.rstrip() == "providers:":
                in_block = True
            continue
        if line[:1] not in (" ", "\t", "-") and stripped:
            break                      # dedented to the next top-level key
        if stripped.startswith("- "):
            v = stripped[2:].strip()
            if v.startswith("id:"):
                v = v[3:].strip()
            out.append(v.strip("'\""))
        elif stripped.startswith("id:"):
            out.append(stripped[3:].strip().strip("'\""))
    return out

bad = 0
found = []
for name in sys.argv[1:]:
    cfg = os.path.join("plugins", name, "evals", "promptfoo", "promptfooconfig.yaml")
    if not os.path.isfile(cfg):
        print(f"MISSING {cfg}", file=sys.stderr); bad += 1; continue
    ids = ids_from(cfg)
    if ids is None:
        bad += 1; continue
    subs = [i for i in ids if i.startswith("openrouter:")]
    if not subs:
        print(f"NO-SUBJECT {name}: declares no 'openrouter:<model>' provider", file=sys.stderr); bad += 1; continue
    found.extend(s.split(":", 1)[1] for s in subs)
for s in sorted(set(found)):
    print(s)
sys.exit(1 if bad else 0)
PY
)" || { echo "::error::could not read subject providers from one or more packs (see above) — nothing was verified." >&2; exit 1; }

if [ -z "$subjects" ]; then
  echo "::error::no subject slugs extracted from $(printf '%s' "$names" | wc -w) pack(s) — nothing was verified." >&2
  exit 1
fi

if [ "$MODE" = "list" ]; then
  printf '%s\n' "$subjects"
  exit 0
fi

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "::error::OPENROUTER_API_KEY is not set — every behavioral pack would grade a model it cannot call." >&2
  exit 1
fi

fail=0
checked=0
while IFS= read -r model; do
  [ -n "$model" ] || continue
  checked=$((checked+1))
  body="$(mktemp)"
  code=$(curl -sS -o "$body" -w '%{http_code}' https://openrouter.ai/api/v1/chat/completions \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -H "content-type: application/json" \
    -d "{\"model\":\"$model\",\"max_tokens\":8,\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}") || code=000
  case "$code" in
    200) echo "subject model '$model' resolved OK — key valid, slug valid, balance sufficient." ;;
    401) echo "::error::subject model '$model': HTTP 401 — the OpenRouter key is invalid or revoked. Every behavioral pack is grading a model it cannot call."; fail=1 ;;
    402) echo "::error::subject model '$model': HTTP 402 — OpenRouter reports insufficient credit. Packs will run and every real-skill row will fail."; fail=1 ;;
    404) echo "::error::subject model '$model': HTTP 404 — the slug no longer exists on OpenRouter. Update it in each pack's promptfooconfig.yaml."; fail=1 ;;
    429) echo "::warning::subject model '$model': HTTP 429 — rate limited right now; not conclusive." ;;
    *)   echo "::error::subject model '$model': HTTP $code — could not confirm the model is callable."; sed -e 's/^/    /' "$body" 2>/dev/null | head -5; fail=1 ;;
  esac
  rm -f "$body"
done <<< "$subjects"

# The load-bearing assertion: a pass must mean a model was actually pinged.
if [ "$checked" -eq 0 ]; then
  echo "::error::verified ZERO subject models despite discovering packs — this check would otherwise be green without checking anything." >&2
  exit 1
fi
echo "verified $checked distinct subject model(s)."
[ "$fail" -eq 0 ]
