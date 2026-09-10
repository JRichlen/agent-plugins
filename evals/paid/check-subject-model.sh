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
# WHAT A GREEN HERE DOES NOT MEAN. A ping is a single 8-token request. OpenRouter
# reserves credit per request against the ones already in flight, so it answers
# 402 "would exceed your available credits given your current in-flight requests"
# for a real pack run while still answering 200 for a ping — and a full CI fan-out
# is ~12 packs x concurrency 3. That is not a hypothetical: on 2026-09-09 this
# check returned 200 for every slug and 11 of 12 behavioral packs were
# simultaneously failing every row with exactly that 402. So the ping proves the
# key and the slug, and it proves NOTHING about whether the account can fund a
# run. The balance probe below is what speaks to funding; it is advisory because
# it depends on a response shape this repo does not control.
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

# Fallback ceiling for a provider that declares no max_tokens of its own.
DEFAULT_PING_TOKENS=8

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
    """Active provider ids only, each paired with the max_tokens that provider
    declares. The token count matters: OpenRouter reserves credit against
    max_tokens, so a ping that asks for 8 tokens succeeds while the pack asking
    for 8192 is refused. Pinging with the pack's own ceiling is what makes the
    preflight predictive instead of merely reassuring."""
    try:
        import yaml
        doc = yaml.safe_load(open(cfg)) or {}
        out = []
        for p in (doc.get("providers") or []):
            pid = p.get("id") if isinstance(p, dict) else p
            mt = ((p.get("config") or {}).get("max_tokens")
                  if isinstance(p, dict) else None)
            if isinstance(pid, str):
                out.append((pid, mt if isinstance(mt, int) and mt > 0 else None))
        return out
    except ImportError:
        pass
    except Exception as e:
        print(f"PARSE-ERROR {cfg}: {e}", file=sys.stderr)
        return None
    # PyYAML absent: walk the providers block by hand, skipping comment lines.
    # max_tokens belongs to the id most recently seen.
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
            out.append([v.strip("'\""), None])
        elif stripped.startswith("id:"):
            out.append([stripped[3:].strip().strip("'\""), None])
        elif stripped.startswith("max_tokens:") and out:
            try:
                out[-1][1] = int(stripped.split(":", 1)[1].strip())
            except ValueError:
                pass
    return [tuple(x) for x in out]

bad = 0
found = []
for name in sys.argv[1:]:
    cfg = os.path.join("plugins", name, "evals", "promptfoo", "promptfooconfig.yaml")
    if not os.path.isfile(cfg):
        print(f"MISSING {cfg}", file=sys.stderr); bad += 1; continue
    ids = ids_from(cfg)
    if ids is None:
        bad += 1; continue
    subs = [(i, mt) for (i, mt) in ids if i.startswith("openrouter:")]
    if not subs:
        print(f"NO-SUBJECT {name}: declares no 'openrouter:<model>' provider", file=sys.stderr); bad += 1; continue
    found.extend((i.split(":", 1)[1], mt) for (i, mt) in subs)
# Ping each slug at the LARGEST ceiling any pack asks for: that is the request
# most likely to be refused, so it is the one worth proving affordable.
worst = {}
for slug, mt in found:
    worst[slug] = max(worst.get(slug) or 0, mt or 0)
for slug in sorted(worst):
    print(f"{slug}\t{worst[slug] or 0}")
sys.exit(1 if bad else 0)
PY
)" || { echo "::error::could not read subject providers from one or more packs (see above) — nothing was verified." >&2; exit 1; }

if [ -z "$subjects" ]; then
  echo "::error::no subject slugs extracted from $(printf '%s' "$names" | wc -w) pack(s) — nothing was verified." >&2
  exit 1
fi

if [ "$MODE" = "list" ]; then
  while IFS="$(printf '\t')" read -r slug mt; do
    [ -n "$slug" ] || continue
    if [ "${mt:-0}" -gt 0 ] 2>/dev/null; then
      echo "$slug (ping reserves max_tokens=$mt, the largest any pack declares)"
    else
      echo "$slug (no max_tokens declared; ping reserves the default $DEFAULT_PING_TOKENS)"
    fi
  done <<< "$subjects"
  exit 0
fi

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "::error::OPENROUTER_API_KEY is not set — every behavioral pack would grade a model it cannot call." >&2
  exit 1
fi

# --- balance probe -----------------------------------------------------------
# Advisory, and deliberately so. It reports what the account says about its own
# credit so a 402 storm is diagnosable BEFORE the packs run, rather than after a
# reviewer reads an empty transcript box. It never fails the run on a shape it
# cannot parse: this repo does not own OpenRouter's response schema, and failing
# closed on an unrecognised field would block CI on a vendor's rename. It DOES
# fail closed on the one unambiguous signal — a remaining balance at or below 0.
kb="$(mktemp)"
kcode=$(curl -sS -o "$kb" -w '%{http_code}' https://openrouter.ai/api/v1/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY") || kcode=000
if [ "$kcode" = "200" ]; then
  remaining="$(jq -r '.data.limit_remaining // empty' "$kb" 2>/dev/null || true)"
  usage="$(jq -r '.data.usage // "?"' "$kb" 2>/dev/null || echo "?")"
  limit="$(jq -r '.data.limit // "unlimited/unknown"' "$kb" 2>/dev/null || echo "?")"
  echo "credit: usage=$usage limit=$limit remaining=${remaining:-<not reported>}"
  case "$remaining" in
    ''|*[!0-9.eE+-]*)
      echo "::warning::OpenRouter did not report a numeric remaining balance, so funding is UNVERIFIED. A pack run can still 402 with every ping below green." ;;
    *)
      if awk -v r="$remaining" 'BEGIN{exit !(r+0 <= 0)}'; then
        echo "::error::OpenRouter reports $remaining credit remaining — the behavioral packs will 402 on every row. Add credit before spending a run."
        fail_balance=1
      fi ;;
  esac
else
  echo "::warning::could not read the OpenRouter key/credit endpoint (HTTP $kcode) — funding is UNVERIFIED; the pings below prove reachability only."
fi
rm -f "$kb"

fail="${fail_balance:-0}"
checked=0
while IFS="$(printf '\t')" read -r model mt; do
  [ -n "$model" ] || continue
  checked=$((checked+1))
  # Reserve what the packs reserve. OpenRouter prices a request against
  # max_tokens, not against what the model actually returns, so an 8-token ping
  # is affordable in situations where every pack row is refused. Observed on
  # 2026-09-10: this check reported reachable with $17.92 remaining while all 12
  # packs got `402 ... you requested up to 8192 tokens, but can only afford
  # 5385`. The ceiling is a reservation, not spend: the reply is still one word.
  tokens="${mt:-0}"
  [ "$tokens" -gt 0 ] 2>/dev/null || tokens="$DEFAULT_PING_TOKENS"
  body="$(mktemp)"
  code=$(curl -sS -o "$body" -w '%{http_code}' https://openrouter.ai/api/v1/chat/completions \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -H "content-type: application/json" \
    -d "{\"model\":\"$model\",\"max_tokens\":$tokens,\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}") || code=000
  case "$code" in
    200) echo "subject model '$model' reachable AND affordable at max_tokens=$tokens — the ceiling the packs actually request." ;;
    401) echo "::error::subject model '$model': HTTP 401 — the OpenRouter key is invalid or revoked. Every behavioral pack is grading a model it cannot call."; fail=1 ;;
    402) echo "::error::subject model '$model': HTTP 402 at max_tokens=$tokens — OpenRouter will not fund a request this size, so every real-skill row in every pack will fail the same way. Remedies, in the vendor's words: add credit, or lower max_tokens in the pack configs to fit the remaining balance."
         sed -e 's/^/    /' "$body" 2>/dev/null | head -3; fail=1 ;;
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
