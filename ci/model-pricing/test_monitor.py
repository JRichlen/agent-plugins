import datetime as dt
import importlib.util
import json
import math
import unittest
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("price_monitor_under_test", HERE / "monitor.py")
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)


MODEL = "z-ai/glm-5.3-flash"
WORKLOAD = {"input_tokens": 1000, "output_tokens": 2000, "cache_read_tokens": 0}
POLICY = {
    "models": [MODEL, "qwen/qwen3.6-plus"],
    "material_usd": "0.02",
    "material_fraction": "0.15",
    "agent": {"enabled": True, "provider": "openrouter", "per_run_usd": "1", "monthly_usd": "2"},
}


def endpoint(tag="provider/fp4", prompt="0.000001", completion="0.000002", **extra):
    value = {"tag": tag, "context_length": 100000, "quantization": "fp4",
             "pricing": {"prompt": prompt, "completion": completion},
             "supported_parameters": ["tools"]}
    value.update(extra)
    return value


def response(model=MODEL, endpoints=None):
    return {"data": {"id": model, "endpoints": endpoints or [endpoint()]}}


class MonitorPureFunctionTests(unittest.TestCase):
    def assert_fault(self, fn, *args, **kwargs):
        with self.assertRaises(monitor.Fault):
            fn(*args, **kwargs)

    def test_actual_policy_is_valid_and_rejects_unfunded_enable_or_ceiling_drift(self):
        live = json.loads((HERE / "policy.json").read_text())
        monitor.validate_policy(live)
        # Enabling the shipped zero-budget policy alone cannot authorize spend.
        unfunded = deepcopy(live)
        unfunded["agent"].update(enabled=True, per_run_usd=0, monthly_usd=0, provider="")
        self.assert_fault(monitor.validate_policy, unfunded)
        for field, value in (("per_run_usd", ".051"), ("monthly_usd", "1.01"),
                             ("max_input_bytes", 32769), ("max_output_tokens", 4097),
                             ("enabled", "false")):
            bad = deepcopy(live)
            bad["agent"][field] = value
            self.assert_fault(monitor.validate_policy, bad)

    def test_normalize_rejects_identity_missing_and_bad_prices(self):
        self.assert_fault(monitor.normalize, "wrong", response(), WORKLOAD)
        self.assert_fault(monitor.normalize, MODEL, {"data": {"id": MODEL, "endpoints": []}}, WORKLOAD)
        for bad in ("nan", "-0.000001", -1, True, "not-a-price"):
            self.assert_fault(monitor.normalize, MODEL, response(endpoints=[endpoint(prompt=bad)]), WORKLOAD)
        self.assert_fault(monitor.normalize, MODEL, response(endpoints=[endpoint(completion=None)]), WORKLOAD)

    def test_normalize_preserves_conditional_pricing_without_discounting(self):
        routes = monitor.normalize(
            MODEL,
            response(endpoints=[endpoint(discount=0.4)]),
            WORKLOAD,
        )
        row = next(iter(routes.values()))
        self.assertFalse(row["comparable"])
        self.assertEqual(row["conditional_pricing"], {"discount": 0.4})
        self.assertIsNone(row["held_mix_usd"])
        self.assertEqual(row["rates_per_million"]["prompt"], "1.000000")
        unknown = endpoint()
        unknown["pricing"]["extra_meter"] = "0.01"
        unknown_row = next(iter(monitor.normalize(MODEL, response(endpoints=[unknown]), WORKLOAD).values()))
        self.assertFalse(unknown_row["comparable"])
        self.assertEqual(unknown_row["conditional_pricing"]["unrecognized_pricing"], {"extra_meter": "0.01"})

    def test_route_identity_separates_provider_tier_context_and_quantization(self):
        routes = monitor.normalize(
            MODEL,
            response(endpoints=[
                endpoint(tag="provider/flex"),
                endpoint(tag="provider/flex", context_length=200000),
                endpoint(tag="other/fp4", quantization="fp8"),
            ]),
            WORKLOAD,
        )
        self.assertEqual(len(routes), 3)
        self.assertEqual({r["service_tier"] for r in routes.values()}, {"flex", "unspecified"})
        self.assertEqual({r["context_length"] for r in routes.values()}, {100000, 200000})
        self.assertEqual({r["quantization"] for r in routes.values()}, {"fp4", "fp8"})
        self.assertEqual(len(monitor.normalize(MODEL, response(endpoints=[endpoint(), endpoint()]), WORKLOAD)), 1)
        self.assert_fault(monitor.normalize, MODEL, response(endpoints=[endpoint(), endpoint(prompt="0.000003")]), WORKLOAD)

    def test_material_change_threshold_and_cumulative_reference(self):
        before = {"route": {"held_mix_usd": "1.000", "rates_per_million": {"prompt": "1", "completion": "1"},
                              "supported_parameters": [], "conditional_pricing": {}, "comparable": True}}
        quiet = deepcopy(before)
        quiet["route"]["held_mix_usd"] = "1.01"
        self.assertEqual(monitor.material_changes(before, quiet, POLICY), [])
        changed = deepcopy(before)
        changed["route"]["held_mix_usd"] = "1.30"
        changes = monitor.material_changes(before, changed, POLICY)
        self.assertEqual(changes[0]["kind"], "rate")
        # A small second change is measured from the retained reference, not the quiet snapshot.
        self.assertEqual(monitor.material_changes(changed, quiet, POLICY), [{"route": "route", "kind": "rate", "before_usd": "1.30", "after_usd": "1.01"}])

    def test_reserve_rejects_ledger_duplicates_missing_key_and_month_exhaustion(self):
        now = "2026-09-05T12:00:00+00:00"
        base = {"schema_version": 1, "reservations": [], "reviewed_fingerprints": []}
        key = {"limit_reset": "monthly", "include_byok_in_limit": True, "limit": "2", "limit_remaining": "2"}
        first = monitor.reserve(base, POLICY, "101", "fp1", key, now)
        self.assertEqual(first["status"], "reserved")
        self.assert_fault(monitor.reserve, base, POLICY, "101", "fp2", key, now)
        self.assert_fault(monitor.reserve, base, POLICY, "102", "fp1", key, now)
        exhausted = {"schema_version": 1, "reservations": [{"month": "2026-09", "run": "old", "reserved_usd": "1.1", "fingerprint": "old"}], "reviewed_fingerprints": []}
        self.assert_fault(monitor.reserve, exhausted, POLICY, "102", "fp2", key, now)
        self.assert_fault(monitor.reserve, {"schema_version": 1, "reservations": [], "reviewed_fingerprints": []}, POLICY, "103", "fp3", {"limit_reset": "daily"}, now)
        self.assert_fault(monitor.reserve, {"schema_version": 1, "reservations": [], "reviewed_fingerprints": []}, POLICY, "104", "fp4", {**key, "limit_remaining": "0.5"}, now)

    def test_validate_proposal_requires_allowlisted_candidate_citation_and_no_secret_like_text(self):
        routes = {"route": {"model": MODEL}}
        good = {"decision": "validate_candidate", "candidate": MODEL, "reason": "matched check", "evidence": ["route"],
                "risks": ["unknown quality"], "validation": ["run acceptance tests"]}
        result = monitor.validate_proposal(good, POLICY, routes)
        self.assertEqual(result["quality_status"].split(" — ")[0], "UNVALIDATED")
        for edit in (
            {"candidate": "not-approved"},
            {"evidence": ["missing-route"]},
            {"reason": "https://example.invalid"},
            {"reason": "Bearer secret"},
        ):
            bad = deepcopy(good)
            bad.update(edit)
            self.assert_fault(monitor.validate_proposal, bad, POLICY, routes)
        self.assert_fault(monitor.validate_proposal, {**good, "risks": []}, POLICY, routes)

    def test_fresh_accepts_recent_and_rejects_invalid_stale_or_future(self):
        now = dt.datetime.now(dt.timezone.utc)
        self.assertIsNone(monitor.fresh(now.isoformat(), 48))
        self.assert_fault(monitor.fresh, (now - dt.timedelta(hours=49)).isoformat(), 48)
        self.assert_fault(monitor.fresh, (now + dt.timedelta(seconds=301)).isoformat(), 48)
        self.assert_fault(monitor.fresh, "not-a-timestamp", 48)


if __name__ == "__main__":
    unittest.main()
