#!/usr/bin/env python3
"""Observe each plugin's concrete workflow artifacts, independently of outcome.

This is artifact adoption, not proof a plugin was loaded or that narrated
operations actually occurred. Logs claiming backup/delete, a copied guard
hash, and generic completion markers provide no evidence here. Correctness
belongs to the separate outcome oracle, so malformed/incomplete workflow
artifacts can show adoption while failing the task.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys


def _repo_root():
    for candidate in pathlib.Path(__file__).resolve().parents:
        if (candidate / ".claude-plugin/marketplace.json").is_file(): return candidate
    raise RuntimeError("cannot locate repo root")


def _find_card(root, card_id):
    match = re.fullmatch(r"([a-z0-9-]+)-(pos|neg|near)-[0-9]+", card_id)
    if not match: return None
    path = root / "evals/agentic/tasks" / match[1] / card_id / "card.json"
    try: card = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError): return None
    return card if card.get("card_id") == card_id else None


def _verdict(repo_root, card_id, ws):
    card = _find_card(repo_root, card_id)
    if card is None: return False, "unknown card identity"
    plugin = card["plugin"]
    def text(name):
        path = ws / name
        return path.read_text(errors="replace") if path.is_file() else ""
    def has(name, pattern=r"\S"):
        return bool(re.search(pattern, text(name), re.I | re.M))
    def data(name):
        try: return json.loads(text(name))
        except (ValueError, TypeError): return None
    def json_items(name, key):
        value = data(name)
        return value.get(key, []) if isinstance(value, dict) else []

    observed = False
    if plugin == "agent-compiler":
        # A compiled artifact's provenance header is evidence of an attempted
        # compilation format, not proof its hash/content is correct.
        observed = has("rendered.md", r"imageHash:\s*sha256:[0-9a-f]+") and has("rendered.md", r"^name:")
    elif plugin == "codebase-design":
        observed = has("docs/design-notes.md", r"^## Candidate") and has("docs/design-notes.md", r"State:|Depth:|Locality:|Seam:")
    elif plugin == "context-handoff":
        observed = (has("HANDOFF.md", r"^# Handoff") and has("HANDOFF.md", r"References|Commit:")) or has("DECISION_LOG.md", r"^CONTINUE:")
    elif plugin == "dev-diary":
        observed = any("tl;dr" in p.read_text(errors="replace").lower() for p in (ws/"entries").glob("**/*.md"))
    elif plugin == "diagnosing-bugs":
        observed = has("hypotheses.md", r"^\d+\. Claim:") and has("hypotheses.md", r"Falsifying test:")
    elif plugin == "docs-hygiene":
        # An actual instruction correction/question, compared with the task's
        # supplied starting text. Merely claiming 'audited' is insufficient.
        start = repo_root / card["task_path"] / "AGENTS.md"
        original = start.read_text() if start.is_file() else ""
        observed = (bool(text("AGENTS.md")) and text("AGENTS.md") != original) or has("QUESTIONS.md", r"AGENTS.md")
    elif plugin == "egress-gate":
        observed = has("EGRESS_MANIFEST.md", r"Sending:|Would send:|Payload:") and has("EGRESS_MANIFEST.md", r"To:|Destination:")
        observed = observed or (has("ASK.md", r"Would send:") and has("ASK.md", r"To:"))
    elif plugin == "eval-ladder":
        tiers = json_items("eval-plan.json", "tiers")
        observed = isinstance(tiers, list) and any(isinstance(tier, dict)
            and type(tier.get("rung")) is int and 0 <= tier["rung"] <= 7
            and all(tier.get(key) for key in ("surface", "blind_spot", "red_control")) for tier in tiers)
    elif plugin == "find-before-build":
        observed = has("RECEIPT.md", r"Searched|legacy_retry") and has("RECEIPT.md", r"rg |manifest|utils/|blocking")
    elif plugin == "fleet-playbook-curator":
        claims = json_items("index.json", "claims")
        observed = isinstance(claims, list) and any(isinstance(c, dict) and all(c.get(k) for k in ("repo", "path", "sha", "claim")) for c in claims)
    elif plugin == "graveyard":
        observed = has("delete-originals.sh", r"gh\s+repo\s+delete") and has("delete-originals.sh", r"bundle|unbundled|empty")
    elif plugin == "grill-me":
        observed = has("INTERVIEW.md", r"Q\d+") and has("INTERVIEW.md", r"➡️")
    elif plugin == "jori":
        cards = json_items("dashboard.json", "cards")
        observed = isinstance(cards, list) and any(isinstance(c, dict) and all(c.get(k) for k in ("id", "owner", "state")) for c in cards)
    elif plugin == "orchestrate":
        observed = has("evidence.md", r"CLAIM:|CHECKED:") and has("evidence.md", r"VERDICT:|REFUTED|CONFIRMED")
    elif plugin == "plugin-factory":
        observed = bool(data("new-plugin.json")) or (bool(data("plugin.json")) and bool(data("marketplace-entry.json")) and has("invariant.md"))
        observed = observed or (has("new_plugin_json.txt") and has("marketplace_entry.txt"))
    elif plugin == "prove-the-undo":
        observed = has("rehearsal.md", r"Restore path:") and has("rehearsal.md", r"Exercised:")
    elif plugin == "recurrence-detector":
        observed = has("candidates.md", r"PROMOTED|WATCHED") and has("candidates.md", r"cite:")
    elif plugin == "redgate":
        observed = any(re.search(r"^phase=", p.read_text(errors="replace"), re.M) for p in (ws/".redgate").glob("*/manifest"))
    elif plugin == "scope-fence":
        observed = has("diff.patch", r"^--- a/") and has("findings.md", r"Found out of scope:")
    elif plugin == "semver-gate":
        observed = has("classification.md", r"Classification:\s*(PATCH|MINOR|MAJOR)") and has("ask.md")
    elif plugin == "stop-rule":
        observed = has("stop-report.md", r"^objective:") and has("stop-report.md", r"^attempt \d+:") and has("stop-report.md", r"^hypothesis \d+:")
    elif plugin == "tailscale-wif":
        start = repo_root / card["task_path"] / "workflow.yml"
        baseline = start.read_text() if start.is_file() else ""
        observed = has("workflow.yml", r"oauth-client-id") and (has("vars.md") or "oauth-client-id" not in baseline)
    elif plugin == "tracer-bullets":
        observed = has("slice.md", r"KEEP") and has("slice.md", r"end.to.end|tracer bullet")
        observed = observed or (has("assessment.md", r"prototype") and has("learnings.md"))
    elif plugin == "verify-before-claim":
        # A measurement receipt must name a real supplied subject; assertions
        # that tests ran or that a poem was counted are not receipts.
        observed = has("claim.md", r"module_test.py") and has("module.py", r"def add") and has("module_test.py", r"unittest")
        observed = observed or (has("check.md", r"CHECK:") and has("poem.txt"))
        observed = observed or (has("claim.md", r"not verified") and has("claim.md", r"network|sandbox|reachability"))
    elif plugin == "voice":
        observed = has("commit-message.txt", r"^Verdict:")
        response = text("response.md").strip()
        observed = observed or (len(response.split()) >= 9 and bool(re.search(r"cache.*eviction|eviction.*cache", response, re.I)))
        observed = observed or has("response.md", r"cannot (provide|run) a second opinion|no subagent")
    elif plugin == "wayfinder":
        tickets = data("tickets.json")
        observed = isinstance(tickets, list) and bool(tickets) and all(isinstance(t, dict) and t.get("id") and t.get("type") and isinstance(t.get("depends_on"), list) for t in tickets)
        observed = observed or has("frontier.md", r"\bT[0-9]+\b")
    else:
        return False, "no plugin-specific adoption observer registered"
    return bool(observed), plugin + (": observable workflow artifact present; invocation provenance unverified" if observed else ": no observable workflow artifact")


def main(argv):
    card_id = os.environ.get("AGENTIC_CARD_ID", "")
    if len(argv)!=2 or not card_id:
        passed, reason = False, "usage: AGENTIC_CARD_ID=<id> verify_adoption.py <workspace>"
    else:
        try: passed, reason = _verdict(_repo_root(), card_id, pathlib.Path(argv[1]).resolve())
        except (OSError, ValueError, TypeError) as exc: passed, reason = False, "invalid artifact: " + str(exc)
    print(json.dumps({"passed":passed,"reason":reason}))
    return 0 if passed else 1


if __name__ == "__main__": raise SystemExit(main(sys.argv))
