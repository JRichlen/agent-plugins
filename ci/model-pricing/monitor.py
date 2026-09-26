#!/usr/bin/env python3
"""Public metadata detector and gated strategy agent. No inference in scan mode."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime

ROOT = Path(__file__).resolve().parents[2]
API = "https://openrouter.ai/api/v1/"
CONFIG_PATHS = ["plugins/jori/evals/promptfoo/promptfooconfig.yaml",
                "evals/routing/promptfooconfig.yaml",
                "evals/routing/trajectory/promptfooconfig.yaml"]


class Fault(Exception):
    """Messages are controller-owned; never include provider response bodies."""


def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def money(value):
    if isinstance(value, bool):
        raise Fault("invalid numeric evidence")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise Fault("invalid numeric evidence") from None
    if not number.is_finite() or number < 0:
        raise Fault("invalid numeric evidence")
    return number


def fresh(value, hours):
    try:
        age = dt.datetime.now(dt.timezone.utc) - dt.datetime.fromisoformat(value)
    except (ValueError, TypeError):
        raise Fault("missing or invalid freshness evidence") from None
    if not -300 <= age.total_seconds() <= hours * 3600:
        raise Fault("stale or future-dated evidence")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise Fault("API redirect refused")


def request(path, payload=None, token=None):
    # Only controller-built API paths; no model/feed-provided URLs or redirects.
    if not re.fullmatch(r"[A-Za-z0-9_./:-]+", path) or ".." in path:
        raise Fault("invalid API path")
    headers = {"Content-Type": "application/json", "User-Agent": "agent-plugins-price-monitor/1"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(API + path, headers=headers,
                                 data=canonical(payload).encode() if payload is not None else None)
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=60) as response:
            date = response.headers.get("Date")
            if not date:
                raise Fault("API response has no freshness date")
            fresh(parsedate_to_datetime(date).isoformat(), 48)
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise Fault("API response exceeds size bound")
            result = json.loads(raw)
    except urllib.error.HTTPError as error:
        raise Fault(f"API request failed with HTTP {error.code}; diagnostic body withheld") from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        raise Fault("API transport or JSON failure; diagnostic body withheld") from None
    if not isinstance(result, dict) or "error" in result:
        raise Fault("API returned an error or invalid object; diagnostic body withheld")
    return result


def rate(value):
    # Public REST prices are dollars/token. Support explicit /M display values too.
    if isinstance(value, str) and "/M" in value:
        return money(value.replace("$", "").split("/M")[0].strip())
    return money(value) * 1_000_000


def normalize(model, response, workload):
    data = response.get("data")
    if not isinstance(data, dict) or data.get("id") != model:
        raise Fault("model identity mismatch")
    endpoints = data.get("endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        raise Fault("model has no verifiable endpoint inventory")
    routes = {}
    for endpoint in endpoints:
        if not isinstance(endpoint, dict):
            raise Fault("invalid endpoint object")
        tag = endpoint.get("tag")
        if not isinstance(tag, str) or not re.fullmatch(r"[a-zA-Z0-9_./:-]{1,160}", tag):
            raise Fault("endpoint has no stable provider tag")
        context = endpoint.get("context_length")
        if not isinstance(context, int) or isinstance(context, bool) or context <= 0:
            raise Fault("endpoint context is unknown")
        quant = endpoint.get("quantization") or "unspecified"
        tier = endpoint.get("service_tier") or ("flex" if "/flex" in tag else "unspecified")
        if not all(isinstance(x, str) and len(x) < 80 for x in (quant, tier)):
            raise Fault("invalid endpoint identity")
        pricing = endpoint.get("pricing")
        if not isinstance(pricing, dict):
            raise Fault("endpoint prices are missing")
        # Preserve condition/override evidence. Do not flatten it into a cheap rate.
        conditions = {key: endpoint[key] for key in
                      ("pricing_overrides", "pricing_tiers", "discount", "is_free") if key in endpoint}
        # API discount is metadata; preserve it, never multiply the listed rate.
        if "discount" in pricing:
            conditions["advertised_discount"] = str(money(pricing["discount"]))
        extra_pricing = set(pricing) - {"prompt", "completion", "input_cache_read", "input_cache_write", "request", "internal_reasoning", "discount"}
        if extra_pricing:
            conditions["unrecognized_pricing"] = {k: pricing[k] for k in sorted(extra_pricing)}
        comparable = not conditions
        rates = {}
        for field in ("prompt", "completion", "input_cache_read", "input_cache_write", "request", "internal_reasoning"):
            if field in pricing:
                try:
                    rates[field] = str(rate(pricing[field]))
                except Fault:
                    comparable = False
        if "prompt" not in rates or "completion" not in rates:
            raise Fault("base text prices cannot be verified")
        if set(pricing) - set(rates) or money(rates.get("request", 0)) or money(rates.get("internal_reasoning", 0)):
            comparable = False
        if workload["cache_read_tokens"] and "input_cache_read" not in rates:
            comparable = False
        key = "|".join((model, tag, quant, str(context), tier))
        parameters = endpoint.get("supported_parameters") or []
        if not isinstance(parameters, list) or not all(isinstance(x, str) and re.fullmatch(r"[a-z_]{1,80}", x) for x in parameters):
            raise Fault("invalid endpoint capabilities")
        estimate = None
        if comparable:
            estimate = str((money(workload["input_tokens"]) * money(rates["prompt"]) +
                            money(workload["output_tokens"]) * money(rates["completion"]) +
                            money(workload["cache_read_tokens"]) * money(rates.get("input_cache_read", 0))) / 1_000_000)
        row = {"model": model, "provider_tag": tag, "quantization": quant,
                       "context_length": context, "service_tier": tier, "rates_per_million": rates,
                       "conditional_pricing": conditions, "comparable": comparable,
                       "held_mix_usd": estimate, "supported_parameters": sorted(set(parameters)),
                       "source": API + "models/" + model + "/endpoints"}
        if key in routes and routes[key] != row:
            raise Fault("conflicting duplicate endpoint identity")
        routes[key] = row  # Repeated identical catalog entries are harmless.
    return routes


def material_changes(before, after, policy):
    changes = []
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        if old is None or new is None:
            changes.append({"route": key, "kind": "added" if old is None else "removed"})
            continue
        if old == new:
            continue
        a, b = old["held_mix_usd"], new["held_mix_usd"]
        # Capability, conditions, or identity changes need review independently of price.
        if any(old.get(k) != new.get(k) for k in ("supported_parameters", "conditional_pricing", "comparable")):
            changes.append({"route": key, "kind": "conditions_or_capabilities"})
        elif a is not None and b is not None:
            delta = abs(money(a) - money(b))
            fraction = delta / money(a) if money(a) else (Decimal(1) if delta else Decimal(0))
            if delta >= money(policy["material_usd"]) and fraction >= money(policy["material_fraction"]):
                changes.append({"route": key, "kind": "rate", "before_usd": a, "after_usd": b})
        elif old["rates_per_million"] != new["rates_per_million"]:
            changes.append({"route": key, "kind": "conditional_rate_review"})
        if new.get("role") == "judge_watch" and old["rates_per_million"] != new["rates_per_million"]:
            changes.append({"route": key, "kind": "judge_rate_review_no_workload_estimate"})
    return changes


def validate_state(state):
    if not isinstance(state, dict) or state.get("schema_version") != 1 or not isinstance(state.get("reservations"), list) or not isinstance(state.get("reviewed_fingerprints"), list):
        raise Fault("missing or invalid durable ledger; manual recovery required")
    seen = set()
    for entry in state["reservations"]:
        if (not isinstance(entry, dict) or not isinstance(entry.get("month"), str)
                or not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", entry["month"])
                or not isinstance(entry.get("run"), str) or not entry["run"]
                or not isinstance(entry.get("fingerprint"), str) or not entry["fingerprint"]
                or entry["run"] in seen):
            raise Fault("invalid durable reservation")
        seen.add(entry.get("run"))
        money(entry.get("reserved_usd"))


def validate_policy(policy):
    agent = policy["agent"]
    models = policy["models"]
    if (policy.get("schema_version") != 1 or not isinstance(models, list) or not 1 <= len(models) <= 8
            or len(set(models)) != len(models) or not all(re.fullmatch(r"[a-z0-9.-]+/[a-z0-9.-]+", x) for x in models)
            or policy["current_subject"] not in models or agent["model"] != "z-ai/glm-5.3-flash"
            or agent["model"] not in models or agent["reasoning_effort"] != "max"
            or policy["judge_watch_model"] != "anthropic/claude-sonnet-5"
            or type(agent["enabled"]) is not bool):
        raise Fault("policy identity or authority is invalid")
    for field, ceiling in (("max_input_bytes", 32768), ("max_output_tokens", 4096)):
        if type(agent[field]) is not int or not 1 <= agent[field] <= ceiling:
            raise Fault("strategy token/input bound is invalid")
    for field, ceiling in (("per_run_usd", ".05"), ("monthly_usd", "1"),
                           ("max_prompt_price_per_million", ".10"), ("max_completion_price_per_million", ".40")):
        if money(agent[field]) > money(ceiling):
            raise Fault("policy exceeds reviewed implementation ceiling")
    if agent["enabled"] and (not money(agent["per_run_usd"]) or not money(agent["monthly_usd"]) or not agent["provider"]):
        raise Fault("enabled strategy requires explicit positive budget and provider")
    if not 0 < money(policy["material_fraction"]) <= 1 or not money(policy["material_usd"]):
        raise Fault("material-change threshold is invalid")
    if type(policy["max_snapshot_age_hours"]) is not int or not 1 <= policy["max_snapshot_age_hours"] <= 48:
        raise Fault("freshness policy is invalid")
    for field in ("input_tokens", "output_tokens", "cache_read_tokens"):
        if type(policy["workload"][field]) is not int or policy["workload"][field] < 0:
            raise Fault("workload mix is invalid")


def reserve(state, policy, run, fingerprint, key_info, now):
    validate_state(state)
    agent = policy["agent"]
    allowance, monthly = money(agent["per_run_usd"]), money(agent["monthly_usd"])
    if not agent["enabled"] or not allowance or not monthly or allowance > monthly:
        raise Fault("strategy spend is disabled or has no approved allowance")
    if not agent["provider"]:
        raise Fault("strategy provider must be explicitly pinned")
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])-\d{2}T.*", now):
        raise Fault("reservation month is invalid")
    if any(x["run"] == run or x["fingerprint"] == fingerprint for x in state["reservations"]):
        raise Fault("run or evidence already reserved; no automatic retry")
    month = now[:7]
    used = sum((money(x["reserved_usd"]) for x in state["reservations"] if x["month"] == month), Decimal(0))
    if used + allowance > monthly:
        raise Fault("monthly reservation allowance exhausted")
    # Dedicated key, never the general CI key. Refuse unbounded / uninspectable limits.
    if key_info.get("limit_reset") != "monthly" or key_info.get("include_byok_in_limit") is not True:
        raise Fault("dedicated key needs a monthly limit including BYOK usage")
    if not money(key_info.get("limit")) or money(key_info["limit"]) > monthly or money(key_info.get("limit_remaining")) < allowance:
        raise Fault("dedicated key allowance/headroom does not satisfy policy")
    entry = {"run": run, "month": month, "reserved_usd": str(allowance), "fingerprint": fingerprint,
             "status": "reserved", "reserved_at": now}
    state["reservations"].append(entry)
    return entry


def validate_proposal(proposal, policy, routes):
    fields = {"decision", "candidate", "reason", "evidence", "risks", "validation"}
    if not isinstance(proposal, dict) or set(proposal) != fields:
        raise Fault("strategy response failed schema validation")
    if proposal["decision"] not in ("hold", "validate_candidate", "stage_update") or proposal["candidate"] not in policy["models"]:
        raise Fault("strategy proposed an unapproved action or model")
    if not isinstance(proposal["reason"], str) or not 1 <= len(proposal["reason"]) <= 1500:
        raise Fault("strategy rationale is invalid")
    for field in ("evidence", "risks", "validation"):
        values = proposal[field]
        if not isinstance(values, list) or not 1 <= len(values) <= 12 or not all(isinstance(x, str) and 1 <= len(x) <= 1000 for x in values):
            raise Fault("strategy response list is invalid")
    if any(x not in routes for x in proposal["evidence"]):
        raise Fault("strategy cited evidence that was not fetched")
    if not any(routes[x]["model"] == proposal["candidate"] for x in proposal["evidence"]):
        raise Fault("strategy omitted evidence for its candidate")
    if re.search(r"https?://|sk-or-|Bearer |github_pat_|gh[pousr]_", canonical(proposal), re.I):
        raise Fault("strategy response contains prohibited URL or credential-shaped text")
    return {"strategy": proposal, "quality_status": "UNVALIDATED — human review and existing gates required",
            "proposed_updates": [] if proposal["decision"] == "hold" else [
                {"path": path, "selector": "providers[0].id", "proposed_value": "openrouter:" + proposal["candidate"],
                 "apply": False, "reasoning_and_provider_settings": "verify and calibrate before applying"}
                for path in CONFIG_PATHS],
            "required_gates": ["Jori real AND negative controls", "routing contracts", "trajectory contracts", "independent judge", "human approval"]}


def strategy_evidence(policy, pending):
    """Deterministic bounded sample; full evidence remains in the scan artifact."""
    routes = pending["snapshot"]["routes"]
    selected = []
    for model in policy["models"]:
        candidates = sorted((k for k in routes if routes[k]["model"] == model),
                            key=lambda k: (money(routes[k]["rates_per_million"]["prompt"])
                                           * policy["workload"]["input_tokens"]
                                           + money(routes[k]["rates_per_million"]["completion"])
                                           * policy["workload"]["output_tokens"], k))
        selected.extend(candidates[:2])
    selected.extend(x["route"] for x in pending["changes"] if x["route"] in routes)
    keys = list(dict.fromkeys(selected))[:16]
    return {"allowed_models": policy["models"], "current_subject": policy["current_subject"],
            "quality_status": "unvalidated", "workload": policy["workload"],
            "fingerprint": pending["fingerprint"], "fetched_at": pending["snapshot"]["fetched_at"],
            "changes": pending["changes"][:16], "routes": {k: routes[k] for k in keys},
            "sampling": "At most two lowest listed text-rate routes/model, then changed routes, capped at 16. This is not a quality or eligibility ranking.",
            "total_routes": len(routes), "total_changes": len(pending["changes"])}


def preflight_route(agent, routes):
    matches = [r for r in routes.values() if r["model"] == agent["model"] and r["provider_tag"] == agent["provider"]]
    if len(matches) != 1:
        raise Fault("pinned strategy endpoint is missing or ambiguous")
    route = matches[0]
    # A numeric advertised discount is retained, never reapplied to listed prices.
    if set(route["conditional_pricing"]) - {"advertised_discount"}:
        raise Fault("strategy endpoint has unpriced conditions")
    rates = route["rates_per_million"]
    if money(rates.get("request", 0)) or money(rates.get("internal_reasoning", 0)) or money(rates.get("input_cache_write", 0)):
        raise Fault("strategy endpoint has additional metering")
    if not {"max_tokens", "response_format", "reasoning"} <= set(route["supported_parameters"]):
        raise Fault("strategy endpoint does not advertise required controls")
    if (money(rates["prompt"]) > money(agent["max_prompt_price_per_million"])
            or money(rates["completion"]) > money(agent["max_completion_price_per_million"])):
        raise Fault("strategy endpoint exceeds approved rate ceilings")
    # Conservative bytes-as-tokens envelope plus chat framing. It is an
    # operational reservation; provider key limits remain the account control.
    estimate = ((agent["max_input_bytes"] + 1024) * money(agent["max_prompt_price_per_million"])
                + agent["max_output_tokens"] * money(agent["max_completion_price_per_million"])) / 1_000_000
    if estimate > money(agent["per_run_usd"]):
        raise Fault("per-run reservation does not cover configured envelope")


class GitState:
    def __init__(self, branch, directory):
        if not re.fullmatch(r"automation/[a-z0-9-]+", branch):
            raise Fault("invalid state branch")
        self.branch, self.directory = branch, directory
        self.git("fetch", "origin", "refs/heads/" + branch)
        self.git("worktree", "add", "--detach", str(directory), "FETCH_HEAD")
        self.path = directory / "state.json"
        try:
            self.data = json.loads(self.path.read_text())
            validate_state(self.data)
        except (OSError, ValueError):
            raise Fault("durable state missing; recover it, never reset the monthly ledger") from None

    def git(self, *args, cwd=None):
        result = subprocess.run(["git", *args], cwd=cwd or ROOT, capture_output=True, text=True)
        if result.returncode:
            raise Fault("state Git operation failed; no inference allowed")
        return result.stdout.strip()

    def save(self):
        write(self.path, self.data)
        self.git("add", "state.json", cwd=self.directory)
        if self.git("diff", "--cached", "--name-only", cwd=self.directory):
            self.git("-c", "user.name=github-actions[bot]", "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
                     "commit", "-m", "Record price monitor evidence and reservations", cwd=self.directory)
            # Non-force push is the concurrency check. Reservation must reach origin.
            self.git("push", "origin", "HEAD:refs/heads/" + self.branch, cwd=self.directory)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["scan", "review"])
    args = parser.parse_args()
    policy = json.loads((ROOT / "ci/model-pricing/policy.json").read_text())
    validate_policy(policy)
    out = ROOT / "work/model-pricing"
    out.mkdir(parents=True, exist_ok=True)
    store = GitState(policy["state_branch"], ROOT / "work" / ("pricing-state-" + args.mode))
    state = store.data
    if args.mode == "scan":
        routes = {}
        for model in policy["models"]:
            routes.update(normalize(model, request("models/" + model + "/endpoints"), policy["workload"]))
        judge = policy["judge_watch_model"]
        judge_routes = normalize(judge, request("models/" + judge + "/endpoints"),
                                 {"input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0})
        for row in judge_routes.values():
            row.update(role="judge_watch", held_mix_usd=None,
                       workload_note="OpenRouter price alert only; actual judge uses direct Anthropic. No subject-token savings calculation or judge replacement authority.")
        routes.update(judge_routes)
        snapshot = {"fetched_at": stamp(), "routes": routes, "workload": policy["workload"]}
        before = state.get("reference_snapshot") or state.get("snapshot")
        changes = material_changes(before["routes"], routes, policy) if before else []
        state["snapshot"] = snapshot
        if not before or changes:
            state["reference_snapshot"] = snapshot
        if changes:
            state["pending"] = {"fingerprint": digest({"routes": routes, "changes": changes}), "changes": changes, "snapshot": snapshot}
        elif state.get("pending") and state["pending"]["snapshot"]["routes"] == routes:
            state["pending"]["snapshot"] = snapshot  # Refresh evidence, preserve dedupe identity.
        store.save()
        write(out / "snapshot.json", snapshot)
        write(out / "status.json", {"status": "material_change" if changes else "baseline" if not before else "unchanged", "changes": changes, "fetched_at": snapshot["fetched_at"]})
        if changes:
            write(out / "strategy-brief.json", state["pending"])
            print("Material price/control change found; strategy evidence staged.")
        return
    agent = policy["agent"]
    pending = state.get("pending")
    if not agent["enabled"] or not pending or pending["fingerprint"] in state["reviewed_fingerprints"]:
        print("No authorized pending strategy review.")
        return
    fresh(pending["snapshot"]["fetched_at"], policy["max_snapshot_age_hours"])
    preflight_route(agent, pending["snapshot"]["routes"])
    token = os.environ.get("PRICE_STRATEGY_KEY")
    if not token:
        raise Fault("dedicated strategy credential is missing")
    prompt = (ROOT / "ci/model-pricing/STRATEGY.md").read_text()
    evidence = strategy_evidence(policy, pending)
    content = canonical(evidence)
    if len((prompt + content).encode()) > agent["max_input_bytes"]:
        raise Fault("strategy input exceeds allowance; narrow watchlist or review evidence manually")
    run = os.environ.get("GITHUB_RUN_ID")
    if not run or not run.isdigit():
        raise Fault("strategy requires a uniquely identified authorized workflow run")
    entry = reserve(state, policy, run, pending["fingerprint"], request("key", token=token).get("data", {}), stamp())
    store.save()  # Irrevocable full reservation BEFORE dispatch; retries cannot reset it.
    payload = {"model": agent["model"], "messages": [{"role": "system", "content": prompt}, {"role": "user", "content": content}],
               "max_tokens": agent["max_output_tokens"], "reasoning": {"effort": agent["reasoning_effort"]},
               "response_format": {"type": "json_object"},
               "provider": {"only": [agent["provider"]], "allow_fallbacks": False, "require_parameters": True,
                            "max_price": {"prompt": agent["max_prompt_price_per_million"], "completion": agent["max_completion_price_per_million"]}}}
    try:
        result = request("chat/completions", payload, token)
        choices = result.get("choices", [])
        if len(choices) != 1 or choices[0].get("finish_reason") != "stop":
            raise Fault("strategy response incomplete; reservation retained")
        proposal = validate_proposal(json.loads(choices[0]["message"]["content"]), policy, evidence["routes"])
        usage = result.get("usage", {})
        cost = money(usage.get("cost"))
        if cost > money(entry["reserved_usd"]):
            raise Fault("reported usage exceeds reservation; stop and inspect account limits")
        entry.update(status="staged", reported_usd=str(cost), completed_at=stamp())
        state["reviewed_fingerprints"].append(pending["fingerprint"])
        proposal.update(evidence_fingerprint=pending["fingerprint"], fetched_at=pending["snapshot"]["fetched_at"],
                        sources={key: row["source"] for key, row in pending["snapshot"]["routes"].items()},
                        requested_model=agent["model"], reported_model=result.get("model"),
                        reserved_usd=entry["reserved_usd"], reported_usd=str(cost))
    except (Fault, ValueError, KeyError, TypeError):
        entry.update(status="unknown_or_failed", completed_at=stamp())
        raise Fault("strategy failed validation or transport; full reservation retained; no automatic retry") from None
    finally:
        store.save()
    write(out / "proposal.json", proposal)
    print("Agent strategy and allowlisted config-change plan staged for human review; no settings applied.")


if __name__ == "__main__":
    try:
        main()
    except (Fault, OSError, ValueError, TypeError, KeyError) as error:
        message = str(error) if isinstance(error, Fault) else "invalid local policy/state or unexpected response; diagnostics withheld"
        print("price-monitor: " + message, file=sys.stderr)
        sys.exit(1)
