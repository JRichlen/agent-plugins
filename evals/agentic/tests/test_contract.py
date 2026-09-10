"""Core-lane tests for evals.agentic.framework.contract and .io.

Covers T01 (record contract schema validity, exercised against small
fixture-owned schemas since the real schemas/*.json files belong to other
lanes and may not exist yet), the vocabulary parts of T09 (forged host-proof
is rejected: assert_native_backed / ForgedProvenance), and the vocabulary
parts of T31 (evidence-class labeling has no promotion path).

Every test asserts observable behavior and is paired with a negative case
that proves the assertion can actually fail.
"""
from __future__ import annotations

import dataclasses
import pathlib
import unittest

from evals.agentic.framework import io
from evals.agentic.framework.contract import (
    ACCOUNTING_STATES,
    ALL_IDS,
    GENESIS_HASH,
    SCORING_INVALID_STATES,
    SCORING_VALID_STATES,
    AdapterClass,
    ArmRole,
    Attempt,
    ContractError,
    ControlKind,
    EvidenceClass,
    ForgedProvenance,
    SignatureClass,
    Stratum,
    TerminalState,
    UNKNOWN,
    Usage,
    Verdict,
    assert_native_backed,
    canonical_json,
    digest,
    new_id,
    now_rfc3339,
)

FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "fixtures" / "contract"
SCHEMAS_DIR = FIXTURES / "schemas"
VALID_DIR = FIXTURES / "valid"
INVALID_DIR = FIXTURES / "invalid"


def _load_mini_schema(name: str) -> io.Schema:
    raw = io.load_json(SCHEMAS_DIR / f"{name}.schema.json")
    return io.Schema(id=raw.get("$id", name), raw=raw)


# ---------------------------------------------------------------------------
# T01 — record contract schema validity
# ---------------------------------------------------------------------------

class SchemaValidity(unittest.TestCase):
    """T01: every fixture under valid/ validates; every fixture under invalid/
    fails, with the offending JSON pointer named in the error. Real schema
    *files* (usage.schema.json etc.) are owned by other lanes and may not
    exist yet on this branch, so this exercises io.py's validator mechanism
    itself against small schemas this lane owns under fixtures/contract/.
    """

    # -- required/additionalProperties: the exact T01 negative control -----

    def test_valid_record_passes(self):
        schema = _load_mini_schema("mini-record")
        instance = io.load_json(VALID_DIR / "mini-record-ok.json")
        schema.validate(instance)  # must not raise
        self.assertEqual(list(schema.iter_errors(instance)), [])

    def test_extra_field_is_rejected_by_pointer(self):
        schema = _load_mini_schema("mini-record")
        instance = io.load_json(INVALID_DIR / "mini-record-extra-field.json")
        with self.assertRaises(io.ValidationError) as ctx:
            schema.validate(instance)
        self.assertEqual(ctx.exception.pointer, "/verdict")
        self.assertEqual(ctx.exception.keyword, "additionalProperties")

    def test_missing_required_key_is_rejected_by_pointer(self):
        schema = _load_mini_schema("mini-record")
        instance = io.load_json(INVALID_DIR / "mini-record-missing-terminal-state.json")
        with self.assertRaises(io.ValidationError) as ctx:
            schema.validate(instance)
        self.assertEqual(ctx.exception.pointer, "/terminal_state")
        self.assertEqual(ctx.exception.keyword, "required")

    def test_negative_control_isinstance_dict_is_vacuous(self):
        """The backlog's named negative control: a test that only asserts
        isinstance(rec, dict) passes both bad records. Prove that claim so
        this suite cannot silently degrade into that vacuous shape."""
        extra = io.load_json(INVALID_DIR / "mini-record-extra-field.json")
        missing = io.load_json(INVALID_DIR / "mini-record-missing-terminal-state.json")
        self.assertIsInstance(extra, dict)
        self.assertIsInstance(missing, dict)
        # ... yet the real validator still rejects both -- isinstance alone proves nothing.
        schema = _load_mini_schema("mini-record")
        self.assertTrue(list(schema.iter_errors(extra)))
        self.assertTrue(list(schema.iter_errors(missing)))

    # -- attempt.control_kind cross-field invariant (§4) --------------------

    def test_valid_control_and_baseline_attempts_pass(self):
        schema = _load_mini_schema("mini-attempt")
        control = io.load_json(VALID_DIR / "mini-attempt-control.json")
        baseline = io.load_json(VALID_DIR / "mini-attempt-baseline.json")
        schema.validate(control)
        schema.validate(baseline)

    def test_baseline_as_control_is_rejected(self):
        """fixtures/contract/invalid/baseline-as-control.json: 'baseline' is
        not a member of ControlKind's wire enum; must fail validation."""
        schema = _load_mini_schema("mini-attempt")
        instance = io.load_json(INVALID_DIR / "baseline-as-control.json")
        errors = list(schema.iter_errors(instance))
        self.assertTrue(errors)
        self.assertTrue(any(e.pointer == "/control_kind" for e in errors))

    def test_baseline_with_control_kind_is_rejected(self):
        """fixtures/contract/invalid/baseline-with-control-kind.json:
        role=baseline, control_kind=nop -- a nop arm mislabelled as the
        baseline. This is the exact defect ground rule 5 exists to catch."""
        schema = _load_mini_schema("mini-attempt")
        instance = io.load_json(INVALID_DIR / "baseline-with-control-kind.json")
        errors = list(schema.iter_errors(instance))
        self.assertTrue(errors, "role=baseline with a non-null control_kind must fail")

    def test_control_kind_enum_has_no_baseline_member(self):
        self.assertEqual(
            set(ControlKind.__members__),
            {"NOP", "INVERSION", "ORACLE", "MUTATION"},
        )
        self.assertNotIn("BASELINE", ControlKind.__members__)

    # -- Attempt.__post_init__ mirrors the schema if/then invariant --------

    def _make_attempt(self, role: ArmRole, control_kind) -> Attempt:
        strat = Stratum("anthropic", "sonnet", "5.1", "medium", "claude-cli")
        usage = Usage(
            model_id="sonnet", reported_by="claude-cli/2.1.263",
            input_tokens=1, output_tokens=1, cache_read_input_tokens=UNKNOWN,
            cache_creation_input_tokens=UNKNOWN, reasoning_tokens=UNKNOWN,
            total_tokens=2, wall_clock_ms=100, cost_usd=None,
        )
        verdict = Verdict(passed=True, verifier_id="v1", reason="ok")
        return Attempt(
            attempt_id="at-1", run_id="run-1", card_id="c1", arm_id="arm-1",
            role=role, control_kind=control_kind, parent_attempt_id=None,
            terminal_state=TerminalState.DELIVERED,
            evidence_class=EvidenceClass.FRAMEWORK, adapter_class=AdapterClass.STUB,
            requested=strat, realized=strat, fallback_flags=(), usage=usage,
            outcome=verdict, adoption=verdict,
            started_at=now_rfc3339(), ended_at=now_rfc3339(),
            session_id=None, event_ids=(), arrived_after_terminal=False,
        )

    def test_attempt_post_init_accepts_matching_role_and_control_kind(self):
        self._make_attempt(ArmRole.CONTROL, ControlKind.NOP)          # ok
        self._make_attempt(ArmRole.BASELINE, None)                    # ok

    def test_attempt_post_init_rejects_baseline_with_control_kind(self):
        with self.assertRaises(ContractError):
            self._make_attempt(ArmRole.BASELINE, ControlKind.NOP)
        with self.assertRaises(ContractError):
            self._make_attempt(ArmRole.CONTROL, None)

    # -- the "null is not UNKNOWN" wire-form rule ---------------------------

    def test_usage_wire_form_accepts_unknown_string_and_null_cost(self):
        schema = _load_mini_schema("mini-usage")
        schema.validate(io.load_json(VALID_DIR / "mini-usage-ok.json"))
        schema.validate(io.load_json(VALID_DIR / "mini-usage-unknown-token.json"))

    def test_usage_wire_form_rejects_null_token(self):
        """null must NOT be accepted as a stand-in for the UNKNOWN sentinel."""
        schema = _load_mini_schema("mini-usage")
        instance = io.load_json(INVALID_DIR / "mini-usage-null-token.json")
        errors = list(schema.iter_errors(instance))
        self.assertTrue(any(e.pointer == "/input_tokens" for e in errors))

    # -- draft 2020-12 "open map": patternProperties + additionalProperties:false

    def test_open_map_accepts_pattern_matching_keys(self):
        schema = _load_mini_schema("mini-open-map")
        schema.validate(io.load_json(VALID_DIR / "mini-open-map-ok.json"))

    def test_open_map_rejects_non_matching_key(self):
        """additionalProperties:false alongside patternProperties constrains
        keys matched by neither -- it does NOT reject every key. A reader
        who thinks it closes the whole object would pass every key; this
        proves the real semantics: only the unmatched key is rejected."""
        schema = _load_mini_schema("mini-open-map")
        instance = io.load_json(INVALID_DIR / "mini-open-map-bad-key.json")
        errors = list(schema.iter_errors(instance))
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].pointer, "/Bad Key!")

    # -- broader keyword coverage: format, multipleOf, uniqueItems ----------

    def test_misc_keywords_valid_instance_passes(self):
        schema = _load_mini_schema("mini-misc")
        schema.validate(io.load_json(VALID_DIR / "mini-misc-ok.json"))

    def test_misc_keywords_iter_errors_does_not_stop_at_first(self):
        schema = _load_mini_schema("mini-misc")
        instance = io.load_json(INVALID_DIR / "mini-misc-bad.json")
        errors = list(schema.iter_errors(instance))
        pointers = {e.pointer for e in errors}
        # bad uuid format, count not a multiple of 5, duplicate tag: three
        # independent violations, all reported, not just the first.
        self.assertIn("/id", pointers)
        self.assertIn("/count", pointers)
        self.assertTrue(any(p.startswith("/tags") for p in pointers))
        self.assertGreaterEqual(len(errors), 3)
        # validate() raises only the first, in document order (properties
        # are declared id, at, count, tags -- id's format error is first).
        with self.assertRaises(io.ValidationError) as ctx:
            schema.validate(instance)
        self.assertEqual(ctx.exception.pointer, "/id")

    # -- schema-compile-time fail-closed behavior ---------------------------

    def test_unsupported_keyword_fails_closed_at_load(self):
        raw = io.load_json(SCHEMAS_DIR / "bad-unsupported-keyword.schema.json")
        with self.assertRaises(io.UnsupportedKeyword):
            io.Schema(id="bad", raw=raw)

    def test_supported_keyword_schema_loads_fine(self):
        """Negative-control counterpart: a schema using only supported
        keywords must NOT raise UnsupportedKeyword."""
        raw = io.load_json(SCHEMAS_DIR / "mini-misc.schema.json")
        io.Schema(id="ok", raw=raw)  # must not raise

    def test_bad_schema_uri_fails_closed(self):
        raw = io.load_json(SCHEMAS_DIR / "bad-schema-uri.schema.json")
        with self.assertRaises(io.SchemaError):
            io.Schema(id="bad", raw=raw)

    def test_unresolvable_ref_fails_closed(self):
        raw = io.load_json(SCHEMAS_DIR / "bad-ref-target.schema.json")
        with self.assertRaises(io.SchemaError):
            io.Schema(id="bad", raw=raw)

    def test_if_without_then_fails_closed(self):
        raw = io.load_json(SCHEMAS_DIR / "bad-if-without-then.schema.json")
        with self.assertRaises(io.UnsupportedKeyword):
            io.Schema(id="bad", raw=raw)

    def test_missing_schema_name_fails_closed(self):
        """A schema name absent from SCHEMA_NAMES must fail closed -- never
        silently resolve to some default or return None."""
        with self.assertRaises(io.SchemaError):
            io.load_schema("not-a-real-schema-name")

    def test_valid_record_passes__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T01. entry.negative_control
        names fixtures/contract/invalid/mini-record-missing-terminal-state.json;
        this must FAIL (the fixture must be rejected) for the T01 catalog
        entry to be considered non-vacuous."""
        return self.test_missing_required_key_is_rejected_by_pointer()

    def test_known_schema_names_are_exactly_the_frozen_eight(self):
        self.assertEqual(
            set(io.SCHEMA_NAMES),
            {"usage", "judgement", "coverage", "card", "run-manifest",
             "attempt", "event", "capability"},
        )


# ---------------------------------------------------------------------------
# T09 (vocabulary) — forged host-proof is rejected
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class _FakeLedger:
    verified: bool
    events: dict  # event_id -> SignatureClass
    host_sessions: frozenset
    # REVIEW FINDING N-06: raw ({"event_id", "run_id", "attempt_id", "kind",
    # "session_id", "host_signature": {"value_class"}}) records, mirroring
    # adapters.LedgerReader.records()'s shape. Defaults to () so every
    # existing caller of _FakeLedger (none of which know about this field)
    # is unaffected -- assert_native_backed's records()-based binding check
    # only fires when there is something in it to bind against.
    event_records: tuple = ()

    def has_event(self, event_id: str) -> bool:
        return event_id in self.events

    def session_ids(self) -> frozenset:
        return frozenset(self.host_sessions) | frozenset({"caller-minted-only"})

    def host_observed_session_ids(self) -> frozenset:
        return frozenset(self.host_sessions)

    def is_verified(self) -> bool:
        return self.verified

    def signature_class(self, event_id: str):
        return self.events.get(event_id)

    def records(self) -> tuple:
        return self.event_records


def _attempt_claiming(
    session_id, event_ids, evidence_class=EvidenceClass.SIMULATED,
    role=ArmRole.TREATMENT, control_kind=None, adapter_class=AdapterClass.NATIVE,
) -> Attempt:
    strat = Stratum("anthropic", "sonnet", "5.1", "medium", "claude-cli")
    usage = Usage(
        model_id="sonnet", reported_by="claude-cli/2.1.263",
        input_tokens=1, output_tokens=1, cache_read_input_tokens=UNKNOWN,
        cache_creation_input_tokens=UNKNOWN, reasoning_tokens=UNKNOWN,
        total_tokens=2, wall_clock_ms=100, cost_usd=None,
    )
    verdict = Verdict(passed=True, verifier_id="v1", reason="ok")
    return Attempt(
        attempt_id="at-1", run_id="run-1", card_id="c1", arm_id="arm-1",
        role=role, control_kind=control_kind, parent_attempt_id=None,
        terminal_state=TerminalState.DELIVERED,
        evidence_class=evidence_class, adapter_class=adapter_class,
        requested=strat, realized=strat, fallback_flags=(), usage=usage,
        outcome=verdict, adoption=verdict,
        started_at=now_rfc3339(), ended_at=now_rfc3339(),
        session_id=session_id, event_ids=event_ids, arrived_after_terminal=False,
    )


class ForgedHostProof(unittest.TestCase):
    """T09 vocabulary: contract.assert_native_backed refuses an attempt's
    claim of native provenance that the host ledger does not corroborate."""

    def test_non_claiming_attempt_is_always_accepted(self):
        attempt = _attempt_claiming(session_id=None, event_ids=(), evidence_class=EvidenceClass.FRAMEWORK)
        ledger = _FakeLedger(verified=False, events={}, host_sessions=frozenset())
        assert_native_backed(attempt, ledger)  # must not raise: nothing was claimed

    def test_claims_native_via_event_ids_alone_is_a_claim(self):
        """N-10: assert_native_backed's own docstring says a claim is 'a
        non-None session_id, a non-empty event_ids tuple, or evidence_class
        == NATIVE_PROVEN' -- Attempt.claims_native must agree. An attempt
        with session_id=None, evidence_class=SIMULATED, but a non-empty
        event_ids tuple must still be treated as claiming native provenance
        (and rejected when the ledger does not back that claim)."""
        attempt = _attempt_claiming(
            session_id=None, event_ids=("ev-invented",), evidence_class=EvidenceClass.SIMULATED,
        )
        self.assertTrue(attempt.claims_native)
        ledger = _FakeLedger(verified=True, events={}, host_sessions=frozenset())
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, ledger)

    def test_claims_native_via_event_ids_alone_is_a_claim__negative(self):
        """Sibling: the same shape but with the event actually host-observed
        in the ledger must be ACCEPTED -- proving the assertion above can
        fail (i.e. is not vacuously true for every ledger)."""
        attempt = _attempt_claiming(
            session_id=None, event_ids=("ev-1",), evidence_class=EvidenceClass.SIMULATED,
        )
        self.assertTrue(attempt.claims_native)
        ledger = _FakeLedger(
            verified=True, events={"ev-1": SignatureClass.HOST_OBSERVED}, host_sessions=frozenset(),
        )
        self.assertIsNone(assert_native_backed(attempt, ledger))

    def test_fully_backed_claim_is_accepted(self):
        ledger = _FakeLedger(
            verified=True,
            events={"ev-1": SignatureClass.HOST_OBSERVED},
            host_sessions=frozenset({"sess-1"}),
        )
        attempt = _attempt_claiming(session_id="sess-1", event_ids=("ev-1",))
        # INTEGRATION FINDING (T52): this method previously had no
        # unittest-style assertion at all -- "must not raise" alone is
        # invisible to registry.run_entry's assertion-counting guard
        # (contract §3.9), which correctly reported it as 0-assertion
        # vacuous when driven through the T09 catalog entry. assert_native_
        # backed returns None on success, so asserting that return value
        # both keeps the "must not raise" property AND registers a real,
        # countable assertion. See the integration lane's final report.
        self.assertIsNone(assert_native_backed(attempt, ledger))

        # REVIEW FINDING N-05: registry.run_entry (the ONLY thing --id T09
        # and T52's --gate sweep ever execute for this catalog entry)
        # invokes exactly this one method and nothing else -- the
        # `__negative` sibling below is checked for mere *existence* by
        # run.py/test_catalog.py, never executed by run_entry. A mutation
        # that makes assert_native_backed an unconditional no-op (e.g.
        # returning immediately after the `claims_native` early-out, before
        # ever reaching a single `raise`) therefore left this one method
        # green: it asserts only that a genuinely-backed claim is ACCEPTED,
        # which such a mutation still satisfies vacuously. Closing that gap
        # from inside the one method the catalog actually runs -- rather
        # than relying on a sibling method nothing calls -- means this
        # single assertion sequence now also proves the function still
        # REJECTS what it must reject, reusing the same ledger fixture so a
        # body-deleting mutation cannot pass by accident.
        forged = _attempt_claiming(session_id="sess-1", event_ids=("ev-does-not-exist",))
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(forged, ledger)

    def test_unknown_event_id_is_forged(self):
        ledger = _FakeLedger(verified=True, events={}, host_sessions=frozenset({"sess-1"}))
        attempt = _attempt_claiming(session_id="sess-1", event_ids=("ev-does-not-exist",))
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, ledger)

    def test_caller_asserted_event_is_forged_not_native(self):
        """This is the exact scenario the handoff calls out: 'event IDs in
        caller JSON alone cannot prove native provenance.' A plausible,
        well-typed event id that exists in the ledger but was only
        caller-asserted must still be rejected."""
        ledger = _FakeLedger(
            verified=True,
            events={"ev-1": SignatureClass.CALLER_ASSERTED},
            host_sessions=frozenset({"sess-1"}),
        )
        attempt = _attempt_claiming(session_id="sess-1", event_ids=("ev-1",))
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, ledger)

    def test_session_id_not_host_observed_is_forged(self):
        """session_ids() (header stat, includes caller-minted ids) must NOT
        be the gate -- only host_observed_session_ids() may satisfy it."""
        ledger = _FakeLedger(
            verified=True,
            events={"ev-1": SignatureClass.HOST_OBSERVED},
            host_sessions=frozenset(),  # caller-minted-only is NOT host-observed
        )
        attempt = _attempt_claiming(session_id="caller-minted-only", event_ids=("ev-1",))
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, ledger)
        # sanity: the id IS in the broader session_ids() header stat
        self.assertIn("caller-minted-only", ledger.session_ids())
        self.assertNotIn("caller-minted-only", ledger.host_observed_session_ids())

    def test_unverified_chain_forges_any_claim(self):
        ledger = _FakeLedger(
            verified=False,
            events={"ev-1": SignatureClass.HOST_OBSERVED},
            host_sessions=frozenset({"sess-1"}),
        )
        attempt = _attempt_claiming(session_id="sess-1", event_ids=("ev-1",))
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, ledger)

    def test_fully_backed_claim_is_accepted__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T09. entry.negative_control
        names fixtures/contract/invalid/forged-native-claim.json -- a
        hand-authored attempt claiming native execution via a caller-asserted
        event id. Must FAIL (be rejected as forged), which is exactly what
        test_caller_asserted_event_is_forged_not_native already proves."""
        return self.test_caller_asserted_event_is_forged_not_native()

    def test_native_proven_with_no_backing_ids_is_forged(self):
        ledger = _FakeLedger(verified=True, events={}, host_sessions=frozenset())
        attempt = _attempt_claiming(
            session_id=None, event_ids=(), evidence_class=EvidenceClass.NATIVE_PROVEN
        )
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, ledger)

    # -----------------------------------------------------------------
    # REVIEW FINDING N-06: a genuine host-observed session id/event id
    # (real, HOST_OBSERVED, chain-verified) does not by itself prove THIS
    # attempt earned it -- it could have been copied from a different,
    # genuinely-approved run. Reproduced against a real adapters.HostLedger
    # in scratch/attack_splice.py; these are the fixture-level regression
    # tests for the two independent gates that close it.
    # -----------------------------------------------------------------

    def test_native_proven_with_non_native_adapter_is_forged(self):
        """A replay/stub adapter cannot become native-proven merely by
        citing a real HOST_OBSERVED session id and event id -- evidence_class
        NATIVE_PROVEN requires adapter_class NATIVE, checked independently of
        what the ledger says about the cited ids."""
        ledger = _FakeLedger(
            verified=True,
            events={"ev-1": SignatureClass.HOST_OBSERVED},
            host_sessions=frozenset({"sess-1"}),
        )
        attempt = _attempt_claiming(
            session_id="sess-1", event_ids=("ev-1",),
            evidence_class=EvidenceClass.NATIVE_PROVEN, adapter_class=AdapterClass.REPLAY,
        )
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, ledger)

    def test_native_proven_with_non_native_adapter_is_forged__negative(self):
        """Same fully-backed claim, adapter_class genuinely NATIVE: accepted.
        Demonstrates the check above discriminates on adapter_class alone,
        not on some accidental property of the fixture."""
        ledger = _FakeLedger(
            verified=True,
            events={"ev-1": SignatureClass.HOST_OBSERVED},
            host_sessions=frozenset({"sess-1"}),
        )
        attempt = _attempt_claiming(
            session_id="sess-1", event_ids=("ev-1",),
            evidence_class=EvidenceClass.NATIVE_PROVEN, adapter_class=AdapterClass.NATIVE,
        )
        self.assertIsNone(assert_native_backed(attempt, ledger))

    def test_event_id_recorded_under_another_run_is_forged(self):
        """has_event()/signature_class() alone cannot tell WHICH run/attempt
        a genuinely HOST_OBSERVED event belongs to -- only records() can.
        _attempt_claiming always builds run_id='run-1'/attempt_id='at-1'; the
        record below is genuinely HOST_OBSERVED but was minted for a
        different run entirely."""
        ledger = _FakeLedger(
            verified=True,
            events={"ev-1": SignatureClass.HOST_OBSERVED},
            host_sessions=frozenset(),
            event_records=(
                {
                    "event_id": "ev-1", "run_id": "run-REAL", "attempt_id": "attempt-REAL",
                    "kind": "turn-ack", "session_id": None,
                    "host_signature": {"value_class": "host-observed"},
                },
            ),
        )
        attempt = _attempt_claiming(
            session_id=None, event_ids=("ev-1",), evidence_class=EvidenceClass.NATIVE_PROVEN,
        )
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, ledger)

    def test_event_id_recorded_under_another_run_is_forged__negative(self):
        """Same event, but its record's run_id/attempt_id genuinely match
        this attempt's own -- accepted."""
        ledger = _FakeLedger(
            verified=True,
            events={"ev-1": SignatureClass.HOST_OBSERVED},
            host_sessions=frozenset(),
            event_records=(
                {
                    "event_id": "ev-1", "run_id": "run-1", "attempt_id": "at-1",
                    "kind": "turn-ack", "session_id": None,
                    "host_signature": {"value_class": "host-observed"},
                },
            ),
        )
        attempt = _attempt_claiming(
            session_id=None, event_ids=("ev-1",), evidence_class=EvidenceClass.NATIVE_PROVEN,
        )
        self.assertIsNone(assert_native_backed(attempt, ledger))

    def test_session_ack_recorded_under_another_run_is_forged(self):
        """host_observed_session_ids() proves SOME run's SESSION_ACK was
        host-observed for this session id -- not that it was THIS attempt's
        run. records() is what lets assert_native_backed tell the two
        apart."""
        ledger = _FakeLedger(
            verified=True,
            events={},
            host_sessions=frozenset({"sess-1"}),
            event_records=(
                {
                    "event_id": "ev-ack", "run_id": "run-OTHER", "attempt_id": "attempt-OTHER",
                    "kind": "session-ack", "session_id": "sess-1",
                    "host_signature": {"value_class": "host-observed"},
                },
            ),
        )
        attempt = _attempt_claiming(session_id="sess-1", event_ids=())
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, ledger)

    def test_session_ack_recorded_under_another_run_is_forged__negative(self):
        """Same session id, its SESSION_ACK genuinely recorded under this
        attempt's own run -- accepted."""
        ledger = _FakeLedger(
            verified=True,
            events={},
            host_sessions=frozenset({"sess-1"}),
            event_records=(
                {
                    "event_id": "ev-ack", "run_id": "run-1", "attempt_id": "at-1",
                    "kind": "session-ack", "session_id": "sess-1",
                    "host_signature": {"value_class": "host-observed"},
                },
            ),
        )
        attempt = _attempt_claiming(session_id="sess-1", event_ids=())
        self.assertIsNone(assert_native_backed(attempt, ledger))


# ---------------------------------------------------------------------------
# T31 (vocabulary) — evidence-class labeling has no promotion path
# ---------------------------------------------------------------------------

class EvidenceClassNoPromotion(unittest.TestCase):
    def test_evidence_class_members_are_exactly_five(self):
        self.assertEqual(
            {m.value for m in EvidenceClass},
            {"framework", "real-fixture", "simulated", "native-proven", "paid-required"},
        )

    def test_frozen_attempt_cannot_be_relabeled_in_place(self):
        """The mechanism ground rule 3 relies on: there is no setter. A
        frozen dataclass makes 'promotion by mutation' a hard runtime error,
        not merely a convention."""
        attempt = _attempt_claiming(session_id=None, event_ids=(), evidence_class=EvidenceClass.SIMULATED)
        self.assertIs(attempt.evidence_class, EvidenceClass.SIMULATED)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            attempt.evidence_class = EvidenceClass.NATIVE_PROVEN  # type: ignore[misc]
        # negative control: the attribute genuinely did not change
        self.assertIs(attempt.evidence_class, EvidenceClass.SIMULATED)

    def test_relabeling_requires_reconstruction_which_assert_native_backed_still_gates(self):
        """Even constructing a *fresh* Attempt with evidence_class=NATIVE_PROVEN
        does not bypass the ledger gate: assert_native_backed still refuses
        it unless the ledger actually backs the claim (see ForgedHostProof)."""
        unbacked = _attempt_claiming(
            session_id="sess-x", event_ids=(), evidence_class=EvidenceClass.NATIVE_PROVEN
        )
        ledger = _FakeLedger(verified=True, events={}, host_sessions=frozenset())
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(unbacked, ledger)


# ---------------------------------------------------------------------------
# General vocabulary sanity: constants, UNKNOWN sentinel, Stratum, digests.
# ---------------------------------------------------------------------------

class UnknownSentinel(unittest.TestCase):
    def test_unknown_is_falsy_and_reprs_as_unknown(self):
        self.assertFalse(bool(UNKNOWN))
        self.assertEqual(repr(UNKNOWN), "UNKNOWN")

    def test_unknown_arithmetic_raises_type_error(self):
        with self.assertRaises(TypeError):
            UNKNOWN + 1  # type: ignore[operator]

    def test_unknown_does_not_equal_zero(self):
        """Negative control: a naive UNKNOWN that coerces to 0 for comparison
        would let `usage.input_tokens == 0` silently pass for an unreported
        field. It must not."""
        self.assertFalse(UNKNOWN == 0)
        self.assertFalse(0 == UNKNOWN)
        self.assertTrue(UNKNOWN == UNKNOWN)


class VocabularyConstants(unittest.TestCase):
    def test_all_ids_has_exactly_52_unique_ids(self):
        self.assertEqual(len(ALL_IDS), 52)
        self.assertEqual(len(set(ALL_IDS)), 52)
        self.assertEqual(ALL_IDS[0], "T01")
        self.assertEqual(ALL_IDS[-1], "T52")

    def test_scoring_states_partition_accounting_states(self):
        self.assertEqual(SCORING_VALID_STATES | SCORING_INVALID_STATES, ACCOUNTING_STATES)
        self.assertEqual(SCORING_VALID_STATES & SCORING_INVALID_STATES, frozenset())

    def test_scoring_states_do_not_swap_cancelled_and_timeout(self):
        """Negative control mirroring T03: CANCELLED must be invalid-for-scoring
        and TIMEOUT_AFTER_DELIVERY must be valid-for-scoring -- a classifier
        that swapped these would still pass a naive partition-only check."""
        self.assertIn(TerminalState.CANCELLED, SCORING_INVALID_STATES)
        self.assertIn(TerminalState.TIMEOUT_AFTER_DELIVERY, SCORING_VALID_STATES)

    def test_genesis_hash_shape(self):
        self.assertEqual(GENESIS_HASH, "0" * 64)
        self.assertEqual(len(GENESIS_HASH), 64)


class StratumRoundTrip(unittest.TestCase):
    def test_key_and_parse_round_trip(self):
        s = Stratum("anthropic", "sonnet", "5.1", "medium", "claude-cli")
        self.assertEqual(s.key(), "anthropic|sonnet|5.1|medium|claude-cli")
        self.assertEqual(Stratum.parse(s.key()), s)

    def test_parse_rejects_wrong_arity(self):
        with self.assertRaises(ContractError):
            Stratum.parse("anthropic|sonnet|5.1")


class CanonicalJsonAndDigest(unittest.TestCase):
    def test_digest_is_stable_under_key_reordering(self):
        a = {"b": 1, "a": 2}
        b = {"a": 2, "b": 1}
        self.assertEqual(digest(a), digest(b))

    def test_digest_changes_with_content(self):
        self.assertNotEqual(digest({"a": 1}), digest({"a": 2}))

    def test_canonical_json_has_no_spaces(self):
        self.assertEqual(canonical_json({"a": 1, "b": [1, 2]}), b'{"a":1,"b":[1,2]}')

    def test_new_id_has_prefix_and_is_unique(self):
        a, b = new_id("run"), new_id("run")
        self.assertTrue(a.startswith("run-"))
        self.assertNotEqual(a, b)


class DataclassRoundTrip(unittest.TestCase):
    def test_usage_to_dict_from_dict_round_trip_with_unknown(self):
        usage = Usage(
            model_id="sonnet", reported_by="claude-cli/2.1.263",
            input_tokens=10, output_tokens=UNKNOWN, cache_read_input_tokens=UNKNOWN,
            cache_creation_input_tokens=0, reasoning_tokens=UNKNOWN,
            total_tokens=10, wall_clock_ms=500, cost_usd=None,
        )
        d = usage.to_dict()
        self.assertEqual(d["output_tokens"], "UNKNOWN")
        self.assertIsNone(d["cost_usd"])
        back = Usage.from_dict(d)
        self.assertEqual(back, usage)
        self.assertIs(back.output_tokens, UNKNOWN)
        self.assertTrue(back.any_unknown)
        self.assertIn("output_tokens", back.unknown_fields())

    def test_from_dict_rejects_unknown_key(self):
        """Negative control: from_dict is strict per contract §2.3."""
        good = {
            "model_id": "sonnet", "reported_by": "claude-cli/2.1.263",
            "input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": "UNKNOWN",
            "cache_creation_input_tokens": "UNKNOWN", "reasoning_tokens": "UNKNOWN",
            "total_tokens": 2, "wall_clock_ms": 10, "cost_usd": None,
        }
        Usage.from_dict(good)  # sanity: the well-formed dict works
        bad = dict(good, extra_field="nope")
        with self.assertRaises(ContractError):
            Usage.from_dict(bad)

    def test_from_dict_rejects_null_for_token_field(self):
        good = {
            "model_id": "sonnet", "reported_by": "claude-cli/2.1.263",
            "input_tokens": 1, "output_tokens": 1, "cache_read_input_tokens": "UNKNOWN",
            "cache_creation_input_tokens": "UNKNOWN", "reasoning_tokens": "UNKNOWN",
            "total_tokens": 2, "wall_clock_ms": 10, "cost_usd": None,
        }
        bad = dict(good, input_tokens=None)
        with self.assertRaises(ContractError):
            Usage.from_dict(bad)


if __name__ == "__main__":
    unittest.main()
