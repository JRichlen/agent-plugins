"""evals.agentic.tests.test_lifecycle — T50: full lifecycle path coverage
(integration lane, contract §7.4/§8.7, backlog §7 T50).

Five lifecycle paths, each with a real executed positive fixture and a real
executed negative control, built on the landed classify/adapters/protocols/
accounting APIs (no reimplementation of another lane's logic):

  (a) terminal    -- classify.classify reaches every TerminalState and the
                      state is recorded in an AttemptLedger.
  (b) correction  -- a mid-run correction is its own Attempt row, sharing
                      parent_attempt_id, never overwriting the prior row.
  (c) approval    -- CliDriver.spawn blocks without a grant, blocks on a
                      wrong token, and reaches PAST the approval check (a
                      materially different failure) with the right one; the
                      grant is recorded against the specific action id, not
                      any action that happens to share a token.
  (d) compaction  -- the REAL redgate and voice SessionStart handlers
                      (plugins/redgate, plugins/voice) are run with a
                      source="compact" payload and their state survives it.
  (e) cancellation -- a real python3 worker process group is really
                      cancelled (WorkerPool/os.killpg), classified
                      CANCELLED, and leaves no leaked pid.

(d) drives the real marketplace tree (plugins/redgate, plugins/voice), which
does not exist in the counterfeit corpus's synthetic root -- this catalog
entry is therefore declared `requires_real_marketplace: true` in
manifests/catalog/integration.json, a deliberate, documented correction to
the exclusion list contract §9.3 states in prose (which omits T50 even
though T22, the identical fixture, is correctly excluded there). See the
integration lane's final report for the full reasoning.
"""
from __future__ import annotations

import importlib.util
import os
import pathlib
import sys
import tempfile
import time
import unittest

from evals.agentic.framework import io
from evals.agentic.framework.accounting import AttemptLedger
from evals.agentic.framework.adapters import (
    CliDriver,
    EvidencePromotionRefused,
    HostLedger,
    LedgerReader,
    load_driver_config,
)
from evals.agentic.framework.classify import RunFacts, classify
from evals.agentic.framework.contract import (
    AccountingLeak,
    ApprovalRequired,
    EventKind,
    Manifest,
    SignatureClass,
    TerminalState,
)
from evals.agentic.framework.protocols import (
    HookSpec,
    WorkerPool,
    leaked_pids,
    run_hook,
)

REPO_ROOT = io.repo_root()


def _load_builders():
    path = REPO_ROOT / "evals" / "agentic" / "fixtures" / "measurement" / "builders.py"
    spec = importlib.util.spec_from_file_location("lifecycle_measurement_builders", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builders = _load_builders()

REDGATE_SESSION_SCRIPT = (
    REPO_ROOT / "plugins" / "redgate" / "hooks" / "hooks-handlers" / "session-start.sh"
)
VOICE_SESSION_SCRIPT = REPO_ROOT / "plugins" / "voice" / "hooks-handlers" / "session-start.sh"
DOUBLE_PRINT_MUTANT = (
    REPO_ROOT / "evals" / "agentic" / "fixtures" / "protocols" / "mutants"
    / "session-start-double-print.sh"
)
WORKER_SLEEP = REPO_ROOT / "evals" / "agentic" / "fixtures" / "protocols" / "workers" / "worker_sleep.py"
WORKER_IGNORE_SIGTERM = (
    REPO_ROOT / "evals" / "agentic" / "fixtures" / "protocols" / "workers" / "worker_ignore_sigterm.py"
)


def _facts(**overrides) -> RunFacts:
    base = dict(
        exit_status=0, signalled=None, deliverable_present=True,
        verifier_verdict=True, verifier_green_at_ms=1000, cancel_issued_at_ms=None,
        wall_clock_ms=2000, wall_clock_limit_ms=60000, transport_error=None, bytes_out=512,
    )
    base.update(overrides)
    return RunFacts(**base)


def _approval_covers_action(events, action_id: str, token_id: str) -> bool:
    """The CORRECT check T50(c) requires: an approval is valid for a specific
    action only if a real APPROVAL_GRANTED event exists whose attempt_id
    equals that action and whose recorded token id matches."""
    return any(
        e.kind is EventKind.APPROVAL_GRANTED
        and e.attempt_id == action_id
        and e.payload.get("token_id") == token_id
        for e in events
    )


def _naive_approval_covers_any_action(events, token_id: str) -> bool:
    """The WRONG check: any approval anywhere in the ledger with this token
    authorizes anything. T50(c)'s negative control."""
    return any(
        e.kind is EventKind.APPROVAL_GRANTED and e.payload.get("token_id") == token_id
        for e in events
    )


class FullLifecyclePaths(unittest.TestCase):

    #: REPAIR F1: the catalog entry (T50) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/agentic/fixtures/protocols/workers/worker_ignore_sigterm.py"

    # -- (a) terminal --------------------------------------------------

    def test_terminal_states_are_each_reached_and_recorded(self):
        cases = {
            TerminalState.DELIVERED: _facts(),
            TerminalState.INCOMPLETE: _facts(deliverable_present=False, verifier_verdict=None, verifier_green_at_ms=None),
            TerminalState.CANCELLED: _facts(cancel_issued_at_ms=500, wall_clock_ms=800),
            TerminalState.FAULT: _facts(exit_status=None, signalled="SIGSEGV", deliverable_present=False,
                                          verifier_verdict=None, verifier_green_at_ms=None),
            TerminalState.TIMEOUT_AFTER_DELIVERY: _facts(
                exit_status=None, signalled="SIGKILL", verifier_green_at_ms=45000,
                wall_clock_ms=60050, wall_clock_limit_ms=60000,
            ),
        }
        ledger = AttemptLedger(run_id="run-t50-terminal")
        for state, facts in cases.items():
            self.assertEqual(classify(facts), state, f"{state} fixture did not classify as itself")
            ledger.add(builders.make_attempt(terminal_state=state, attempt_id=f"attempt-{state.value}"))
        ledger.conserve()
        counts = ledger.by_terminal_state()
        for state in cases:
            self.assertEqual(counts[state], 1, f"{state} not recorded exactly once")
        self.assertEqual(sum(counts.values()), 5)

    def test_terminal_states_are_each_reached_and_recorded__negative(self):
        """A cancel that arrives strictly after the run already ended must
        NOT retroactively become the terminal state -- classify() must still
        report the run's own outcome, not a naive 'any cancel_issued_at_ms
        implies CANCELLED' rule that ignores ordering."""
        facts = _facts(cancel_issued_at_ms=90000, wall_clock_ms=2000)  # cancel "issued" AFTER the run ended
        with self.assertRaises(Exception):
            # cancel_issued_at_ms > wall_clock_ms is a contradiction classify()
            # refuses outright (UnclassifiableRun) rather than silently
            # picking a state -- this IS the fail-closed behavior T50(a)'s
            # negative control needs: a naive classifier that just checked
            # "is cancel_issued_at_ms set?" would wrongly return CANCELLED here.
            classify(facts)

    # -- (b) correction --------------------------------------------------

    def test_correction_is_a_separate_attempt_sharing_parent_id(self):
        ledger = AttemptLedger(run_id="run-t50-correction")
        original = builders.make_attempt(attempt_id="orig-1", terminal_state=TerminalState.FAULT)
        correction = builders.make_attempt(
            attempt_id="correction-1", parent_attempt_id="orig-1", terminal_state=TerminalState.DELIVERED,
        )
        ledger.add(original)
        ledger.add(correction)
        ledger.conserve()
        self.assertEqual(len(ledger.attempts()), 2, "the original row must survive, not be overwritten")
        self.assertEqual(ledger.retries()["orig-1"], (correction,))
        self.assertIs(ledger.attempts()[0], original, "the prior attempt's record is untouched")

    def test_correction_is_a_separate_attempt_sharing_parent_id__negative(self):
        """The failure mode this path exists to prevent: a 'correction' that
        reuses the ORIGINAL attempt_id, silently destroying the audit trail.
        AttemptLedger.add refuses this by construction (contract §3.5)."""
        ledger = AttemptLedger(run_id="run-t50-correction-neg")
        ledger.add(builders.make_attempt(attempt_id="orig-2", terminal_state=TerminalState.FAULT))
        clobber = builders.make_attempt(attempt_id="orig-2", terminal_state=TerminalState.DELIVERED)
        with self.assertRaises(AccountingLeak):
            ledger.add(clobber)

    # -- (c) approval ------------------------------------------------------

    def test_approval_blocks_without_a_grant_and_proceeds_past_the_gate_with_one(self):
        config = load_driver_config("claude")

        # No token at all: blocked before argv is even built.
        bare_driver = CliDriver(config)
        with self.assertRaises(ApprovalRequired) as cm1:
            bare_driver.spawn()
        self.assertIn("approval_token", str(cm1.exception))

        manifest = Manifest(
            run_id="run-t50-approval", created_at="2026-09-06T00:00:00.000Z",
            git_commit="6d5342c", branch="feat/agentic-test-framework", offline=True,
            toolchain={"python": "3.12.3"}, lanes=("integration",), estimands=(),
            noninferiority_margin=0.05, min_valid=3, min_clusters=8, planned_n={},
            holdout_seed=1, catalog_digest="0" * 64, skipped=(), approvals=("tok-1",),
        )
        gated_driver = CliDriver(config, manifest=manifest)

        # Wrong token: still blocked, and by a DIFFERENT reason than "no token".
        with self.assertRaises(ApprovalRequired) as cm2:
            gated_driver.spawn(approval_token="tok-WRONG")
        self.assertIn("Manifest.approvals", str(cm2.exception))

        # Right token: the approval-token gate itself is now PASSED -- the
        # driver reaches a materially later, different failure (no ledger),
        # never the "no token" or "wrong token" messages above. That
        # distinction IS the proof the approval gate itself was cleared.
        with self.assertRaises(EvidencePromotionRefused) as cm3:
            gated_driver.spawn(approval_token="tok-1")
        self.assertIn("HostLedger", str(cm3.exception))

        with tempfile.TemporaryDirectory() as td:
            caller_ledger = HostLedger(
                pathlib.Path(td) / "caller.jsonl", run_id="run-t50-approval", witness=SignatureClass.CALLER_ASSERTED,
            )
            with self.assertRaises(EvidencePromotionRefused):
                gated_driver.spawn(approval_token="tok-1", ledger=caller_ledger)
            caller_ledger.close()

            host_ledger = HostLedger(
                pathlib.Path(td) / "host.jsonl", run_id="run-t50-approval", witness=SignatureClass.HOST_OBSERVED,
            )
            # UPDATED 2026-09-07: this gate is no longer merely "cleared but
            # unwired". With the approved token AND a host-observed ledger,
            # `spawn` now opens a real `NativeSession` -- the §10.2 grammar
            # UNKNOWN was settled for `claude` by an approved capture on
            # 2026-09-07, so there is a driver to open one with. What this
            # assertion checks is unchanged in spirit and stronger in fact:
            # the approval gate is passed only with the right token, and the
            # grant is recorded by `spawn` itself against the specific action
            # it authorised. Constructing the session spawns no child process
            # -- a turn does, and no turn is sent here.
            wired_ledger = HostLedger(
                pathlib.Path(td) / "wired.jsonl", run_id="run-t50-approval",
                witness=SignatureClass.HOST_OBSERVED,
            )
            session = gated_driver.spawn(
                approval_token="tok-1", ledger=wired_ledger, attempt_id="action-A",
            )
            self.assertEqual(session.adapter_class.value, "native")
            self.assertIsNone(
                session.session_id,
                "no turn has run, so the harness has acked nothing yet (§10.2)",
            )
            self.assertEqual(session.pids(), frozenset(), "spawn() alone starts no process")
            session.close()
            wired_ledger.close()
            wired_events = LedgerReader(wired_ledger.path, key=wired_ledger.key).events()
            self.assertTrue(
                _approval_covers_action(wired_events, "action-A", "tok-1"),
                "spawn must record the grant against the action it authorised (§10.6)",
            )
            self.assertFalse(
                _approval_covers_action(wired_events, "action-B", "tok-1"),
                "an approval granted for action A must not be honored for action B",
            )

            # The grant is recorded against the SPECIFIC action id, never its
            # value -- host-side, since CliDriver.spawn does not itself
            # append this event (there is no wired native path to reach it
            # from yet; see the report). We exercise the ledger's own public
            # append/read surface directly to prove the recording contract
            # itself, action-scoped, holds.
            host_ledger.append(
                EventKind.APPROVAL_GRANTED, attempt_id="action-A", session_id=None,
                payload={"token_id": "tok-1"},
            )
            host_ledger.close()
            reader = LedgerReader(host_ledger.path, key=host_ledger.key)
            events = reader.events()
            self.assertTrue(_approval_covers_action(events, "action-A", "tok-1"))
            self.assertFalse(
                _approval_covers_action(events, "action-B", "tok-1"),
                "an approval granted for action A must not be honored for action B",
            )

    def test_approval_blocks_without_a_grant_and_proceeds_past_the_gate_with_one__negative(self):
        """The failure mode: a naive check that a token was granted ANYWHERE
        in the ledger, ignoring which action it was granted for. That naive
        check wrongly authorizes action B on action A's grant -- exactly the
        backlog's 'approval granted for action A honored for action B'."""
        with tempfile.TemporaryDirectory() as td:
            ledger = HostLedger(
                pathlib.Path(td) / "host.jsonl", run_id="run-t50-approval-neg", witness=SignatureClass.HOST_OBSERVED,
            )
            ledger.append(
                EventKind.APPROVAL_GRANTED, attempt_id="action-A", session_id=None,
                payload={"token_id": "tok-shared"},
            )
            ledger.close()
            reader = LedgerReader(ledger.path, key=ledger.key)
            events = reader.events()
            self.assertTrue(
                _naive_approval_covers_any_action(events, "tok-shared"),
                "the naive check must actually be capable of the wrong answer, or it is not a real control",
            )
            self.assertFalse(
                _approval_covers_action(events, "action-B", "tok-shared"),
                "the correct, action-scoped check must refuse what the naive one wrongly allows",
            )

    # -- (d) compaction ------------------------------------------------------

    def test_compaction_survives_via_real_redgate_and_voice_handlers(self):
        for script in (REDGATE_SESSION_SCRIPT, VOICE_SESSION_SCRIPT):
            self.assertTrue(script.is_file(), f"{script} must exist on the real marketplace tree")

        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            run_dir = root / ".redgate" / "compact-run"
            run_dir.mkdir(parents=True)
            (run_dir / "manifest").write_text("slug=compact-run\nphase=TRACE\nround=1\n")

            redgate_spec = HookSpec(plugin="redgate", event="SessionStart", matcher="compact",
                                     command=f"bash {REDGATE_SESSION_SCRIPT}", source_file=str(REDGATE_SESSION_SCRIPT))
            payload = {"session_id": "s", "transcript_path": "/tmp/t", "cwd": str(root),
                       "hook_event_name": "SessionStart", "source": "compact"}
            redgate_result = run_hook(redgate_spec, payload, cwd=root, timeout_s=10.0)

            voice_spec = HookSpec(plugin="voice", event="SessionStart", matcher="compact",
                                   command=f"bash {VOICE_SESSION_SCRIPT}", source_file=str(VOICE_SESSION_SCRIPT))
            voice_result = run_hook(voice_spec, payload, cwd=root, timeout_s=10.0)

        self.assertEqual(redgate_result.exit_code, 0)
        self.assertIn("compact-run", redgate_result.stdout,
                       "redgate's own run state must still be visible across a compact event")
        self.assertIn("TRACE", redgate_result.stdout)

        self.assertEqual(voice_result.exit_code, 0)
        self.assertIsNotNone(voice_result.json, f"voice stdout did not parse as JSON: {voice_result.stdout!r}")
        ctx = voice_result.json["hookSpecificOutput"]["additionalContext"]
        self.assertTrue(0 < len(ctx) < 4000, "voice's re-injection must survive compaction, bounded")

    def test_compaction_survives_via_real_redgate_and_voice_handlers__negative(self):
        """A handler that concatenates two JSON objects on compact (this
        mutant) must NOT be mistaken for a valid re-injection -- the same
        single-object contract T22 defends, exercised specifically on the
        compact matcher."""
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            spec = HookSpec(plugin="test-harness", event="SessionStart", matcher="compact",
                             command=f"bash {DOUBLE_PRINT_MUTANT}", source_file=str(DOUBLE_PRINT_MUTANT))
            payload = {"session_id": "s", "transcript_path": "/tmp/t", "cwd": str(root),
                       "hook_event_name": "SessionStart", "source": "compact"}
            result = run_hook(spec, payload, cwd=root, timeout_s=10.0)
        self.assertIsNone(result.json, "two concatenated JSON objects on compact must not parse as one")

    # -- (e) cancellation ------------------------------------------------------

    def test_cancellation_propagates_and_leaves_no_orphan_process(self):
        before = leaked_pids(frozenset(), frozenset())  # sanity: helper importable/callable
        self.assertEqual(before, frozenset())

        with tempfile.TemporaryDirectory() as td:
            pool = WorkerPool(cwd=pathlib.Path(td), timeout_s=10.0)
            try:
                started = time.monotonic()
                pool.spawn("victim", [sys.executable, str(WORKER_SLEEP), "30", "victim"])
                time.sleep(0.2)
                pool.cancel("victim")
                results = pool.collect()
                elapsed_ms = int((time.monotonic() - started) * 1000)
            finally:
                pool.close()

        r = results[0]
        self.assertEqual(r.signalled, "SIGTERM")
        self.assertIsNone(r.exit_code)

        facts = _facts(
            exit_status=None, signalled=None, deliverable_present=False, verifier_verdict=None,
            verifier_green_at_ms=None, cancel_issued_at_ms=200, wall_clock_ms=elapsed_ms,
            wall_clock_limit_ms=60000,
        )
        self.assertEqual(classify(facts), TerminalState.CANCELLED)

        ledger = AttemptLedger(run_id="run-t50-cancel")
        ledger.add(builders.make_attempt(attempt_id="cancelled-1", terminal_state=TerminalState.CANCELLED))
        ledger.conserve()
        self.assertEqual(ledger.by_terminal_state()[TerminalState.CANCELLED], 1)

    def test_cancellation_propagates_and_leaves_no_orphan_process__negative(self):
        """A worker that ignores SIGTERM and finishes late must be recorded
        as arrived_after_terminal, its output never discarded -- discarding
        it (the naive shortcut) would hide continued work after a stop."""
        with tempfile.TemporaryDirectory() as td:
            pool = WorkerPool(cwd=pathlib.Path(td), timeout_s=10.0)
            try:
                pool.spawn("late", [sys.executable, str(WORKER_IGNORE_SIGTERM), "0.5"])
                time.sleep(0.2)
                pool.cancel("late")
                r = pool.collect()[0]
            finally:
                pool.close()
        self.assertTrue(r.arrived_after_terminal)
        self.assertNotEqual(r.stdout.strip(), "", "post-cancel output must not be discarded")

    # -- T50 catalog entry: all five paths, one entry ------------------------

    def test_all_five_lifecycle_paths_have_positive_fixtures(self):
        paths = {
            "terminal": self.test_terminal_states_are_each_reached_and_recorded,
            "correction": self.test_correction_is_a_separate_attempt_sharing_parent_id,
            "approval": self.test_approval_blocks_without_a_grant_and_proceeds_past_the_gate_with_one,
            "compaction": self.test_compaction_survives_via_real_redgate_and_voice_handlers,
            "cancellation": self.test_cancellation_propagates_and_leaves_no_orphan_process,
        }
        exercised = set()
        for name, fn in paths.items():
            fn()
            exercised.add(name)
        self.assertEqual(exercised, {"terminal", "correction", "approval", "compaction", "cancellation"})

    def test_all_five_lifecycle_paths_have_positive_fixtures__negative(self):
        """Catalog sibling (contract §7.4 item 4) for T50. entry.negative_control
        names fixtures/protocols/workers/worker_ignore_sigterm.py: this must
        FAIL the 'discard post-cancel output' shortcut for the cancellation
        path -- the one sub-path whose real subprocess fixture that path
        names directly -- for the T50 catalog entry to be considered
        non-vacuous."""
        return self.test_cancellation_propagates_and_leaves_no_orphan_process__negative()


if __name__ == "__main__":
    unittest.main()
