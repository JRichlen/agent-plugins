"""Adapter-lane tests: T25-T31 (implementation contract §3.12, §5, §10).

Read the naming before reading the assertions. Four of these seven items are
`approval_gate: native-required`, and the only forms of them that exist here are
named `*__offline_form`. That suffix is load-bearing: T26-T29 exercise the
session/turn/resume/cancel/ledger *logic* against replayed streams and real
`python3` workers, and none of them is evidence that a harness ever ran. §10.5
says it plainly -- "no test may claim native evidence from a simulated
subprocess" -- and the catalog prints those four `BLOCKED - approval required`
rather than passed.

What IS closed here, and closed against real artifacts:

* **T25** runs the *installed* `claude --help` and `codex exec --help` as real
  subprocesses and refuses any template flag they do not list. No table of known
  flags appears in `adapters.py`, so a CLI upgrade reds this instead of
  producing argv the CLI silently ignores.
* **T30** parses hand-authored usage records (labelled as such, per the backlog)
  and asserts every absent field is `UNKNOWN`, plus a source scan for the
  `.get(name, 0)` coercion.
* **T31** derives evidence classes and proves there is no promotion path.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import tempfile
import unittest
import uuid

from evals.agentic.framework import adapters, io, protocols
from evals.agentic.framework.adapters import (
    AdapterClass,
    live_group_members,
    ChainVerification,
    CliDriver,
    DriverConfig,
    HostLedger,
    JsonPathSpec,
    LedgerReader,
    ReplaySession,
    StreamGrammar,
    assert_flags_supported,
    attach_session,
    check_fresh_isolation,
    declared_flags,
    dry_run,
    evidence_class_for,
    installed_help,
    load_driver_config,
    load_grammar,
    parse_usage,
    worker_evidence_class,
)
from evals.agentic.framework.contract import (
    UNKNOWN,
    ApprovalRequired,
    Attempt,
    ContractError,
    EvidenceClass,
    EvidencePromotionRefused,
    EventKind,
    FlagNotSupported,
    ForgedProvenance,
    Manifest,
    SignatureClass,
    assert_native_backed,
)

REPO = io.repo_root()
NATIVE = REPO / "evals" / "agentic" / "fixtures" / "native"
REPLAY = NATIVE / "replay"
FRAMEWORK_DIR = REPO / "evals" / "agentic" / "framework"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def synthetic_grammar() -> StreamGrammar:
    """Load `replay/synthetic-offline-form.grammar.json`.

    Deliberately NOT `adapters.load_grammar`, which raises. The grammar in
    `fixtures/native/replay/` is a vocabulary this lane invented for the offline
    forms; keeping it off `load_grammar`'s search path means there is no code
    path on which a synthetic vocabulary could be mistaken for a captured one.
    """
    raw = io.load_json(REPLAY / "synthetic-offline-form.grammar.json")
    return StreamGrammar(
        name=raw["name"],
        session_ack=JsonPathSpec(match=raw["session_ack"]["match"],
                                 extract=raw["session_ack"]["extract"]),
        turn_ack=JsonPathSpec(match=raw["turn_ack"]["match"],
                              extract=raw["turn_ack"]["extract"]),
        usage=JsonPathSpec(match=raw["usage"]["match"], extract=raw["usage"]["extract"]),
        session_id_field=raw["session_id_field"],
        turn_index_field=raw["turn_index_field"],
    )


def code_only(path: pathlib.Path) -> str:
    """Return `path`'s source with every comment and string literal removed.

    Source scans in this file are looking for what the module *does*, not what
    it says about itself. A scan over raw text flags the docstring that explains
    why `.get(name, 0)` is banned, which trains the next reader to delete the
    explanation rather than the defect. `tokenize` draws the line exactly where
    the Python grammar does.
    """
    import io as _stdio
    import tokenize

    kept: list[str] = []
    with path.open("rb") as handle:
        for token in tokenize.tokenize(handle.readline):
            if token.type in (tokenize.COMMENT, tokenize.STRING):
                continue
            kept.append(token.string)
    del _stdio
    return "\n".join(kept)


class _TempMixin(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="agentic-adapter-")
        self.tmp = pathlib.Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def caller_ledger(self, name: str = "events.jsonl") -> HostLedger:
        ledger = HostLedger(
            self.tmp / name, run_id="run-offline-form",
            witness=SignatureClass.CALLER_ASSERTED,
        )
        self.addCleanup(ledger.close)
        return ledger

    def host_ledger(self, name: str = "host.jsonl") -> HostLedger:
        ledger = HostLedger(
            self.tmp / name, run_id="run-host", witness=SignatureClass.HOST_OBSERVED,
        )
        self.addCleanup(ledger.close)
        return ledger


class _NoSpawn:
    """Context manager that reds the test if anything reaches `subprocess.Popen`.

    §8.5 asks for exactly this: proof that the dry-run path spawns no child,
    established without `strace`. It wraps the attribute the whole stdlib routes
    through (`subprocess.run`, `check_output` and friends all construct a
    `Popen`), so a call through any of them is caught.
    """

    def __init__(self, case: unittest.TestCase) -> None:
        self.case = case
        self.calls: list[tuple] = []
        self._real = subprocess.Popen

    def __enter__(self) -> "_NoSpawn":
        outer = self

        class _Trap(outer._real):  # type: ignore[misc, valid-type]
            def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
                outer.calls.append((args, kwargs))
                raise AssertionError(
                    f"the offline path spawned a child process: {args!r}"
                )

        subprocess.Popen = _Trap  # type: ignore[misc]
        return self

    def __exit__(self, *exc: object) -> None:
        subprocess.Popen = self._real  # type: ignore[misc]


# ===========================================================================
# T25 — flag conformance against the REAL installed binaries
# ===========================================================================

class DriverArgvConformance(_TempMixin):
    """T25. Real `--help` of the real installed CLIs; no hand-written flag table."""

    def test_driver_flags_conform_to_installed_help_and_spawn_needs_approval(self):
        """The catalog anchor for T25. Runs both installed CLIs' help for real."""
        checked = 0
        for name in ("claude", "codex"):
            config = load_driver_config(name)
            self.assertTrue(os.path.isabs(config.binary), f"{name}: binary must be absolute")
            self.assertTrue(os.path.isfile(config.binary), f"{name}: binary must exist")

            help_text = installed_help(config)
            self.assertGreater(len(help_text), 200, f"{name}: --help produced nothing usable")

            flags = declared_flags(config)
            self.assertGreater(len(flags), 3, f"{name}: template declares almost no flags")
            for flag in flags:
                self.assertRegex(
                    help_text, rf"(?<![\w-]){re.escape(flag)}(?![\w-])",
                    f"{name}: {flag} is emitted by the driver but absent from the "
                    f"installed {' '.join(config.help_argv)} output",
                )
            assert_flags_supported(config)   # raises FlagNotSupported on any drift
            checked += 1

        self.assertEqual(checked, 2)

        # spawn() without an approval token raises, and does so before Popen.
        config = load_driver_config("claude")
        driver = CliDriver(config)
        with _NoSpawn(self) as trap:
            with self.assertRaises(ApprovalRequired):
                driver.spawn(mode="fresh", model="m")
        self.assertEqual(trap.calls, [], "spawn() must refuse before touching subprocess")

    def test_driver_flags_conform_to_installed_help_and_spawn_needs_approval__negative(self):
        """Catalog sibling (§7.4 item 4) for T25.

        `entry.negative_control` names `fixtures/native/drivers/invented-flag.json`,
        a config whose template emits `--session-name` -- a flag `claude --help`
        does not list. The whole point of reading the installed help is that this
        must be a hard error, not a token the CLI silently ignores. The same
        assertion is run against a `--dangerously-*` config, which is refused
        even though the CLI genuinely supports it.
        """
        invented = load_driver_config("invented-flag")
        self.assertIn("--session-name", declared_flags(invented))
        with self.assertRaises(FlagNotSupported) as caught:
            assert_flags_supported(invented)
        self.assertEqual(getattr(caught.exception, "flag", None), "--session-name")

        dangerous = load_driver_config("dangerous-flag")
        help_text = installed_help(dangerous)
        self.assertIn(
            "--dangerously-skip-permissions", help_text,
            "the point of this control is that the CLI DOES support the flag",
        )
        with self.assertRaises(FlagNotSupported) as caught:
            assert_flags_supported(dangerous)
        self.assertEqual(
            getattr(caught.exception, "flag", None), "--dangerously-skip-permissions"
        )

    def test_build_argv_is_pure_and_drops_inapplicable_flags(self):
        config = load_driver_config("claude")
        driver = CliDriver(config)
        with _NoSpawn(self):
            argv = driver.build_argv(
                mode="fresh", model="m", effort=None,
                session_id="00000000-0000-4000-8000-000000000000",
                permission_mode="plan", allowed_tools="Read", workspace="/w",
                system_append="x", mcp_config="/w/mcp.json",
            )
        self.assertNotIn("--effort", argv, "a None slot must drop its flag, not pass a literal")
        self.assertNotIn("n/a", argv)
        self.assertIn("--model", argv)
        self.assertEqual(argv[0], config.binary, "argv[0] is the resolved absolute binary")

    def test_spawn_refuses_every_token_that_is_not_in_the_manifests_approvals(self):
        """§10.6. No default, no env fallback, no --yes, and no Popen on any path."""
        manifest = Manifest(
            run_id="run-approved", created_at="2026-09-06T00:00:00.000Z",
            git_commit="0" * 40, branch="feat/agentic-test-framework", offline=True,
            toolchain={"python": "3.12.3"}, lanes=("adapter",),
            estimands=(), noninferiority_margin=0.05, min_valid=5, min_clusters=8,
            planned_n={}, holdout_seed=1, catalog_digest="0" * 64, skipped=(),
            approvals=("approval-native-2026-09-06",),
        )
        driver = CliDriver(load_driver_config("claude"), manifest=manifest)
        slots = dict(
            model="m", effort=None, session_id="00000000-0000-4000-8000-000000000000",
            permission_mode="plan", allowed_tools="Read", workspace="/w",
            system_append="x", mcp_config="/w/mcp.json",
        )
        with _NoSpawn(self) as trap:
            for token in (None, "", "approval-something-else"):
                with self.assertRaises(ApprovalRequired, msg=repr(token)):
                    driver.spawn(approval_token=token, **slots)
            # The approved token gets past §10.6 and is stopped by §10.5: a
            # native spawn may only write to a host-observed ledger, and there
            # is still no captured grammar to parse the session it would open.
            with self.assertRaises((EvidencePromotionRefused, ApprovalRequired)):
                driver.spawn(
                    approval_token="approval-native-2026-09-06",
                    ledger=self.caller_ledger("would-be-native.jsonl"), **slots,
                )
        self.assertEqual(trap.calls, [], "no approval path may reach subprocess here")

    def test_driver_config_is_frozen_data_loaded_from_a_fixture(self):
        config = load_driver_config("claude")
        self.assertIsInstance(config, DriverConfig)
        with self.assertRaises(Exception):
            config.binary = "/bin/false"  # type: ignore[misc]
        self.assertEqual(config.adapter_class, AdapterClass.NATIVE)
        self.assertEqual(config.grammar, "claude-stream-json")

    def test_build_argv_rejects_an_unknown_mode(self):
        driver = CliDriver(load_driver_config("codex"))
        with self.assertRaises(ContractError):
            driver.build_argv(mode="teleport")

    def test_optional_argv_covers_fresh_resume_and_fork_for_both_drivers(self):
        for name, expected in (("claude", {"fresh", "resume", "fork"}),
                               ("codex", {"fresh", "resume", "fork"})):
            config = load_driver_config(name)
            self.assertEqual(set(config.optional_argv), expected, name)

    def test_no_dangerously_flag_appears_in_either_shipped_template(self):
        """§10.1's source/config scan. The handoff bans bypass-permissions mode."""
        for name in ("claude", "codex"):
            blob = (adapters.DRIVERS_DIR() / f"{name}.json").read_text(encoding="utf-8")
            self.assertNotIn("--dangerously-", blob, name)
            self.assertNotIn("--allow-dangerously-", blob, name)
        code = code_only(FRAMEWORK_DIR / "adapters.py")
        self.assertNotIn(
            "--dangerously-", code,
            "adapters.py must not emit a --dangerously-* flag (comments and docstrings "
            "are stripped before this scan, so only real code counts)",
        )

    def test_dry_run_prints_planned_argv_and_never_spawns(self):
        """The §8.5 acceptance text, asserted rather than eyeballed."""
        for name in ("claude", "codex"):
            with _NoSpawn(self) as trap:
                rendered = dry_run(name)
            self.assertEqual(trap.calls, [])
            self.assertIn("argv: ", rendered)
            self.assertIn(
                "adapter_class=native (NOT SPAWNED — no approval token)", rendered, name
            )

    def test_env_is_an_allowlist_and_never_inherits_os_environ(self):
        marker = "AGENTIC_ADAPTER_MUST_NOT_LEAK"
        os.environ[marker] = "1"
        self.addCleanup(os.environ.pop, marker, None)
        planned = CliDriver(load_driver_config("codex")).dry_run(
            sandbox="read-only", workspace="/w", extra_dir="/x", model="m",
            last_message_path="/w/last.txt", home="/h",
        )
        self.assertNotIn(marker, planned.env)
        self.assertEqual(set(planned.env), {"PATH", "HOME", "LANG", "CODEX_HOME"})


# ===========================================================================
# T26 — session and turn acknowledgments (native-required; offline form only)
# ===========================================================================

class SessionTurnAcks(_TempMixin):
    """T26 offline form. Replays a SYNTHETIC stream; proves nothing about a CLI."""

    def test_session_and_turn_acks_bind_to_harness_reported_ids__offline_form(self):
        ledger = self.caller_ledger()
        session = ReplaySession(
            str(REPLAY / "two-turn-acked.jsonl"), synthetic_grammar(), ledger,
            attempt_id="attempt-0001",
        )
        self.assertEqual(session.session_id, "harness-sess-AAAA")
        first = session.send("hello")
        second = session.send("again")
        self.assertTrue(first.acked)
        self.assertTrue(second.acked)
        self.assertEqual((first.index, second.index), (0, 1))
        self.assertEqual(session.turns, 2)
        self.assertIsNotNone(first.ack_event_id)

        reader = LedgerReader(ledger.path, key=None)
        acks = [e for e in reader.events() if e.kind is EventKind.TURN_ACK]
        self.assertEqual(len(acks), 2, "one ledger TURN_ACK per stream ack, not per write")
        self.assertEqual(
            {e.session_id for e in acks}, {"harness-sess-AAAA"},
            "every event binds to the id the stream reported",
        )

        # The whole point of the *__offline_form suffix: a replay is SIMULATED,
        # and the ack ids are caller-asserted, so the native gate stays shut.
        chain = reader.verify_chain()
        self.assertTrue(chain.ok)
        self.assertEqual(
            evidence_class_for(session.adapter_class, chain), EvidenceClass.SIMULATED
        )
        self.assertEqual(reader.host_observed_session_ids(), frozenset())

    def test_session_and_turn_acks_bind_to_harness_reported_ids__offline_form__negative(self):
        """Catalog sibling (§7.4 item 4) for T26.

        `entry.negative_control` names `replay/no-session-ack.jsonl`. Two
        failures the happy path cannot see:

        1. a stream that never announces a session leaves `session_id` None --
           §10.2 item 2 -- and the caller-minted uuid passed to `--session-id`
           is recorded only in a caller-asserted SESSION_OPEN payload, never
           promoted into the ack;
        2. `replay/self-counted-turns.jsonl` has no `turn_ack` record at all.
           An adapter that counted its own writes to stdin would report
           `acked=True` here. It must report False.
        """
        minted = str(uuid.uuid4())
        ledger = self.caller_ledger("no-ack.jsonl")
        session = ReplaySession(
            str(REPLAY / "no-session-ack.jsonl"), synthetic_grammar(), ledger,
            caller_minted_session_id=minted,
        )
        self.assertIsNone(
            session.session_id, "a caller-minted uuid is not a session acknowledgment"
        )
        reader = LedgerReader(ledger.path, key=None)
        opens = [e for e in reader.events() if e.kind is EventKind.SESSION_OPEN]
        self.assertEqual(len(opens), 1)
        self.assertEqual(opens[0].payload["caller_minted_session_id"], minted)
        self.assertIsNone(opens[0].session_id)
        self.assertEqual(
            reader.signature_class(opens[0].event_id), SignatureClass.CALLER_ASSERTED
        )
        self.assertNotIn(minted, reader.host_observed_session_ids())

        ledger2 = self.caller_ledger("self-counted.jsonl")
        session2 = ReplaySession(
            str(REPLAY / "self-counted-turns.jsonl"), synthetic_grammar(), ledger2
        )
        turn = session2.send("does this get an ack it never received?")
        self.assertFalse(
            turn.acked,
            "an adapter that synthesizes turn boundaries from its own writes would "
            "report True here; the ack must come off the harness's stream",
        )

    def test_an_unacked_session_can_never_be_native_proven(self):
        ledger = self.caller_ledger("unacked.jsonl")
        session = ReplaySession(
            str(REPLAY / "no-session-ack.jsonl"), synthetic_grammar(), ledger
        )
        session.send("x")
        reader = LedgerReader(ledger.path, key=None)
        self.assertIsNone(session.session_id)
        self.assertNotEqual(
            evidence_class_for(session.adapter_class, reader.verify_chain()),
            EvidenceClass.NATIVE_PROVEN,
        )


# ===========================================================================
# T27 — resume, fork, fresh isolation (native-required; offline form only)
# ===========================================================================

class ResumeAndIsolation(_TempMixin):
    """T27 offline form. State-machine logic against replayed streams."""

    def test_resume_continues_the_same_session_and_fork_records_its_parent__offline_form(self):
        grammar = synthetic_grammar()
        ledger = self.caller_ledger("session.jsonl")

        first = ReplaySession(str(REPLAY / "two-turn-acked.jsonl"), grammar, ledger)
        first.send("one")
        first.send("two")
        self.assertEqual(first.turns, 2)

        # Resume: same ledger, same harness-reported id, turns continue.
        resumed = ReplaySession(str(REPLAY / "resume-continues.jsonl"), grammar, ledger)
        resumed.turns = first.turns          # the driver's high-water mark
        resumed.send("three")
        self.assertEqual(
            resumed.session_id, first.session_id,
            "a resume that reports a DIFFERENT harness session id is a failure, "
            "not a rename (§10.3)",
        )
        self.assertEqual(resumed.turns, 3, "turn index continues monotonically")
        self.assertEqual(
            LedgerReader(ledger.path, key=None).path, ledger.path,
            "resumed events append to the SAME ledger",
        )

        # Fork: new id, parent recorded in the SESSION_OPEN payload.
        fork_ledger = self.caller_ledger("fork.jsonl")
        forked = ReplaySession(
            str(REPLAY / "fork-child.jsonl"), grammar, fork_ledger,
            parent_session_id=first.session_id,
        )
        self.assertNotEqual(forked.session_id, first.session_id)
        opens = [
            e for e in LedgerReader(fork_ledger.path, key=None).events()
            if e.kind is EventKind.SESSION_OPEN
        ]
        self.assertEqual(opens[0].payload["parent_session_id"], first.session_id)

        # Fresh: a different id AND a clean workspace AND no recalled context.
        workspace = self.tmp / "ws"
        workspace.mkdir()
        (workspace / "task.txt").write_text("card input\n", encoding="utf-8")
        before = protocols.snapshot_tree(workspace)
        fresh = ReplaySession(str(REPLAY / "fresh-other-session.jsonl"), grammar,
                              self.caller_ledger("fresh.jsonl"))
        probe = fresh.send("what did we discuss a moment ago?")
        after = protocols.snapshot_tree(workspace)
        report = check_fresh_isolation(
            prior_session_id=first.session_id,
            fresh_session_id=fresh.session_id,
            before=before, after=after,
            probe_answered_as_unknown="no record" in probe.text.lower(),
        )
        self.assertTrue(report.isolated, report.why_not())

    def test_resume_continues_the_same_session_and_fork_records_its_parent__offline_form__negative(self):
        """Catalog sibling (§7.4 item 4) for T27.

        `entry.negative_control` names `fixtures/native/isolation/carried-over`,
        a workspace whose files survived into the "fresh" session. Checking only
        that the ids differ is explicitly insufficient (§10.3): the contaminating
        state is on disk, not in the id, and this workspace has two distinct ids
        sitting on top of a fully contaminated tree.
        """
        workspace = self.tmp / "contaminated"
        workspace.mkdir()
        before = protocols.snapshot_tree(workspace)
        for source in sorted((NATIVE / "isolation" / "carried-over").iterdir()):
            if source.is_file():
                (workspace / source.name).write_bytes(source.read_bytes())
        after = protocols.snapshot_tree(workspace)

        id_only = ("harness-sess-AAAA" != "harness-sess-CCCC")
        self.assertTrue(id_only, "the ids DO differ -- that is exactly the trap")

        report = check_fresh_isolation(
            prior_session_id="harness-sess-AAAA",
            fresh_session_id="harness-sess-CCCC",
            before=before, after=after,
            probe_answered_as_unknown=True,
        )
        self.assertTrue(report.distinct_session_id)
        self.assertFalse(report.isolated, "carried-over artifacts must fail isolation")
        self.assertIn("leaked-artifact.txt", report.carried_over_paths)

        leaked = check_fresh_isolation(
            prior_session_id="harness-sess-AAAA",
            fresh_session_id="harness-sess-CCCC",
            before=before, after=before,
            probe_answered_as_unknown=False,
        )
        self.assertFalse(leaked.isolated, "a recalled prior turn must fail isolation too")

    def test_a_fresh_session_reusing_the_prior_id_is_not_isolated(self):
        report = check_fresh_isolation(
            prior_session_id="s1", fresh_session_id="s1",
            before={}, after={}, probe_answered_as_unknown=True,
        )
        self.assertFalse(report.isolated)
        self.assertFalse(report.distinct_session_id)


# ===========================================================================
# T28 — cancellation (native-required; offline form uses REAL subprocesses)
# ===========================================================================

class CancellationPath(_TempMixin):
    """T28 offline form. Real `python3` workers, cancelled via the process group."""

    def _pool(self) -> protocols.WorkerPool:
        pool = protocols.WorkerPool(cwd=self.tmp, timeout_s=20.0)
        self.addCleanup(pool.close)
        return pool

    def test_cancel_kills_the_process_group_and_tags_late_output__offline_form(self):
        import time
        worker = NATIVE / "workers" / "worker_late_output.py"
        pool = self._pool()
        before = protocols._live_descendant_pids(os.getpid())
        pid = pool.spawn("w1", ["python3", str(worker)])
        # Let the worker reach its SIGTERM handler. Cancelling before it installs
        # one would prove nothing about late output -- the default disposition
        # would simply kill it, silently, which is the case the next test covers.
        time.sleep(0.6)

        ledger = self.caller_ledger("cancel.jsonl")
        session = attach_session(
            ledger=ledger, adapter_class=AdapterClass.STUB, pool=pool,
            worker_id="w1", worker_pid=pid, attempt_id="attempt-cancel",
        )
        session.cancel(grace_s=0.6)
        session.close()
        after = protocols._live_descendant_pids(os.getpid())

        self.assertEqual(
            protocols.leaked_pids(before, after), frozenset(),
            "cancel must leave no orphan in the process tree",
        )
        self.assertEqual(session.pids(), frozenset(), "pids() after close() must be empty")

        kinds = [e.kind for e in LedgerReader(ledger.path, key=None).events()]
        self.assertIn(EventKind.CANCEL_ISSUED, kinds)
        self.assertIn(EventKind.CANCEL_OBSERVED, kinds)
        self.assertLess(
            kinds.index(EventKind.CANCEL_ISSUED), kinds.index(EventKind.CANCEL_OBSERVED),
            "the issue must be recorded BEFORE the signal, the observation after",
        )
        self.assertIn(EventKind.LATE_OUTPUT, kinds)
        self.assertTrue(session.arrived_after_terminal)

        late = [
            e for e in LedgerReader(ledger.path, key=None).events()
            if e.kind is EventKind.LATE_OUTPUT
        ]
        self.assertFalse(late[0].payload["credited"], "late output is recorded, not credited")

    def test_cancel_kills_the_process_group_and_tags_late_output__offline_form__negative(self):
        """Catalog sibling (§7.4 item 4) for T28.

        `entry.negative_control` names
        `fixtures/native/workers/worker_ignores_sigterm.py`: it swallows SIGTERM
        and forks a grandchild into the same group. A cancel implemented as
        SIGKILL on the parent pid alone produces an identical-looking ledger and
        leaks two processes. Signalling the GROUP and then diffing the live pid
        set is the assertion that catches it -- so this test proves both that the
        worker really does survive SIGTERM, and that the real cancel still reaps
        it.
        """
        worker = NATIVE / "workers" / "worker_ignores_sigterm.py"

        import time

        # 1. The worker genuinely survives a group SIGTERM.
        stubborn = self._pool()
        stubborn.spawn("s1", ["python3", str(worker)])
        time.sleep(0.6)
        stubborn.cancel("s1")
        time.sleep(0.6)
        still_live = protocols._live_descendant_pids(os.getpid())
        self.assertTrue(
            still_live,
            "the control is only meaningful if the worker actually ignores SIGTERM",
        )
        stubborn.close()

        # 2. The real cancel path escalates to SIGKILL on the GROUP and reaps it.
        pool = self._pool()
        before = protocols._live_descendant_pids(os.getpid())
        pid = pool.spawn("w2", ["python3", str(worker)])
        time.sleep(0.6)
        pgid = os.getpgid(pid)
        self.assertGreaterEqual(
            len(live_group_members(pgid)), 2,
            "the control needs the worker to have forked into its own group",
        )
        ledger = self.caller_ledger("stubborn.jsonl")
        session = attach_session(
            ledger=ledger, adapter_class=AdapterClass.STUB,
            pool=pool, worker_id="w2", worker_pid=pid,
        )
        started = time.monotonic()
        session.cancel(grace_s=0.4)
        elapsed = time.monotonic() - started

        # The load-bearing assertion. A cancel that signals only the parent pid
        # leaves the forked grandchild alive in the group, and WorkerPool's own
        # 30s collect() timeout would eventually rescue it -- so the survivor
        # count is witnessed by cancel() BEFORE collect() runs, and the elapsed
        # time proves the rescue path was not what cleaned up.
        observed = [
            e for e in LedgerReader(ledger.path, key=None).events()
            if e.kind is EventKind.CANCEL_OBSERVED
        ]
        self.assertEqual(
            observed[0].payload["group_survivors"], 0,
            "SIGTERM alone is not a cancel, and neither is SIGKILL on the parent "
            "pid: the process GROUP must be empty when cancel() returns",
        )
        self.assertLess(
            elapsed, 10.0,
            "cancel() must reap the group itself, not wait for WorkerPool's "
            "collect() timeout to do it",
        )

        session.close()
        after = protocols._live_descendant_pids(os.getpid())
        self.assertEqual(
            protocols.leaked_pids(before, after), frozenset(),
            "no orphan may survive the cancel",
        )

    def test_a_cancelled_replay_records_unconsumed_output_as_late(self):
        ledger = self.caller_ledger("replay-cancel.jsonl")
        session = ReplaySession(
            str(REPLAY / "late-output-after-cancel.jsonl"), synthetic_grammar(), ledger
        )
        session.send("go")
        self.assertGreater(session.remaining, 0)
        session.cancel(grace_s=0.0)
        self.assertTrue(session.arrived_after_terminal)
        kinds = [e.kind for e in LedgerReader(ledger.path, key=None).events()]
        self.assertIn(EventKind.LATE_OUTPUT, kinds)

    def test_a_worker_subprocess_is_real_fixture_evidence_never_native(self):
        self.assertEqual(worker_evidence_class(real_process=True), EvidenceClass.REAL_FIXTURE)
        self.assertEqual(worker_evidence_class(real_process=False), EvidenceClass.FRAMEWORK)
        with self.assertRaises(EvidencePromotionRefused):
            attach_session(
                ledger=self.caller_ledger("nope.jsonl"), adapter_class=AdapterClass.NATIVE,
                pool=self._pool(), worker_id="never",
            )


# ===========================================================================
# T29 — the host event ledger (native-required; offline form only)
# ===========================================================================

class EventLedgerIntegrity(_TempMixin):
    """T29 offline form. The chain algorithm, the witness rule, the four tampers."""

    def test_chain_verifies_and_names_the_first_bad_index_per_tamper__offline_form(self):
        genuine = LedgerReader(NATIVE / "ledgers" / "genuine-caller-asserted.jsonl", key=None)
        chain = genuine.verify_chain()
        self.assertTrue(chain.ok)
        self.assertIsNone(chain.first_bad_index)
        self.assertEqual(chain.events, 8)
        self.assertEqual(chain.host_observed, 0)

        expected = {
            "edited-field": ("edited-field", 3),
            "deleted-entry": ("deleted-entry", 3),
            "inserted-entry": ("inserted-entry", 4),
            "swapped-pair": ("swapped-pair", 3),
        }
        for name, (reason, index) in expected.items():
            with self.subTest(tamper=name):
                verdict = LedgerReader(NATIVE / "tamper" / f"{name}.jsonl", key=None).verify_chain()
                self.assertFalse(verdict.ok, name)
                self.assertEqual(verdict.reason, reason, name)
                self.assertEqual(verdict.first_bad_index, index, name)

        # A host-observed ledger mints its own key and refuses a supplied one.
        with self.assertRaises(EvidencePromotionRefused):
            HostLedger(
                self.tmp / "supplied.jsonl", run_id="r",
                witness=SignatureClass.HOST_OBSERVED, key=b"\x00" * 32,
            )
        host = self.host_ledger()
        ack = host.append(
            EventKind.SESSION_ACK, attempt_id="a1", session_id="sess-real",
            payload={"source": "harness"},
        )
        reader = LedgerReader(host.path, key=host.key)
        self.assertTrue(reader.verify_chain().ok)
        self.assertTrue(reader.is_verified())
        self.assertEqual(reader.host_observed_session_ids(), frozenset({"sess-real"}))
        self.assertEqual(reader.signature_class(ack.event_id), SignatureClass.HOST_OBSERVED)

        # The key is never written anywhere in the workspace.
        blob = host.path.read_bytes()
        self.assertNotIn(host.key, blob)
        self.assertIn(b'"key_id":"run-run-host"', blob)

    def test_chain_verifies_and_names_the_first_bad_index_per_tamper__offline_form__negative(self):
        """Catalog sibling (§7.4 item 4) for T29.

        `entry.negative_control` names `fixtures/native/tamper/edited-field.jsonl`.
        Two failures a hash-chain-only test would miss:

        1. **A verifier without the key must not bless.** The genuine ledger's
           chain is intact, yet `is_verified()` is False without a key -- §5.3.
        2. **A relinked forgery passes the chain.** `tamper/forged-host-observed.jsonl`
           relabels an entry host-observed with 64 hex of noise and recomputes
           every downstream hash, which a forger can do because the algorithm is
           public. `verify_chain().ok` is True. The HMAC is what refuses it, and
           `signature_class` downgrades the entry rather than taking its word.
        """
        genuine = LedgerReader(NATIVE / "ledgers" / "genuine-caller-asserted.jsonl", key=None)
        self.assertTrue(genuine.verify_chain().ok)
        self.assertFalse(
            genuine.is_verified(),
            "an intact hash chain is not provenance; without the key nothing is blessed",
        )

        forged = LedgerReader(NATIVE / "tamper" / "forged-host-observed.jsonl", key=None)
        verdict = forged.verify_chain()
        self.assertTrue(
            verdict.ok, "the forger relinked the chain -- that is the whole point"
        )
        self.assertEqual(verdict.host_observed, 1)
        self.assertFalse(forged.is_verified())
        self.assertEqual(
            forged.host_observed_session_ids(), frozenset(),
            "a host-observed claim with an unverifiable HMAC yields no blessed session id",
        )
        ack = next(
            r for r in forged.records() if r["kind"] == EventKind.SESSION_ACK.value
        )
        self.assertEqual(
            forged.signature_class(ack["event_id"]), SignatureClass.CALLER_ASSERTED,
            "a bad HMAC downgrades the entry; it does not get the benefit of the doubt",
        )

    def test_append_derives_value_class_from_the_witness_with_no_override(self):
        """§10.5 item 3 by construction, not by convention."""
        import inspect
        signature = inspect.signature(HostLedger.append)
        self.assertEqual(
            set(signature.parameters) - {"self"},
            {"kind", "attempt_id", "session_id", "payload"},
            "append() must expose no value_class / witness / signature parameter",
        )
        caller = self.caller_ledger("derived.jsonl")
        event = caller.append(
            EventKind.TURN_ACK, attempt_id="a", session_id="s", payload={}
        )
        self.assertIs(event.host_signature.value_class, SignatureClass.CALLER_ASSERTED)
        self.assertEqual(event.host_signature.algo, "none")
        self.assertIsNone(event.host_signature.value)

    def test_the_ledger_file_is_opened_append_only(self):
        ledger = self.caller_ledger("append-only.jsonl")
        ledger.append(EventKind.RUN_START, attempt_id=None, session_id=None, payload={})
        first = ledger.path.read_text(encoding="utf-8")
        ledger.append(EventKind.RUN_END, attempt_id=None, session_id=None, payload={})
        second = ledger.path.read_text(encoding="utf-8")
        self.assertTrue(second.startswith(first), "an append must never rewrite a prefix")
        self.assertEqual(len(second.splitlines()), 2)

    def test_every_ledger_entry_validates_against_the_event_schema(self):
        schema = io.load_schema("event")
        checked = 0
        for record in io.read_jsonl(NATIVE / "ledgers" / "genuine-caller-asserted.jsonl"):
            schema.validate(record)
            checked += 1
        host = self.host_ledger("schema.jsonl")
        host.append(EventKind.SPAWN, attempt_id="a", session_id=None, payload={"pid": 1})
        for record in io.read_jsonl(host.path):
            schema.validate(record)
            checked += 1
        self.assertGreater(checked, 8)


# ===========================================================================
# T30 — telemetry unknowns (real-fixture, closable offline)
# ===========================================================================

class TelemetryUnknowns(_TempMixin):
    """T30. Absent means UNKNOWN. Never 0, never omitted, never inferred."""

    def test_absent_usage_fields_parse_as_unknown_and_never_zero(self):
        grammar = synthetic_grammar()
        checked = 0
        for name in ("claude-hand-authored", "codex-hand-authored"):
            fixture = io.load_json(NATIVE / "usage" / f"{name}.json")
            self.assertIn(
                "HAND-AUTHORED, NOT RECORDED", fixture["PROVENANCE"],
                "the fixture must say what it is; no recorded CLI output exists here",
            )
            usage = parse_usage(
                fixture["record"], grammar,
                model_id=fixture["record"]["model"], reported_by=f"{name}/hand-authored",
            )
            self.assertEqual(
                sorted(usage.unknown_fields()), sorted(fixture["expected_unknown_fields"]), name
            )
            for field in fixture["expected_unknown_fields"]:
                self.assertIs(getattr(usage, field), UNKNOWN, f"{name}.{field}")
                self.assertNotEqual(getattr(usage, field), 0, f"{name}.{field}")
            self.assertIsNone(usage.cost_usd, "cost is 'not computed', never 0.0")
            self.assertTrue(usage.any_unknown)
            checked += 1
        self.assertEqual(checked, 2)

        # Reported fields are stored verbatim, alongside the reporting model id.
        claude = io.load_json(NATIVE / "usage" / "claude-hand-authored.json")
        usage = parse_usage(claude["record"], grammar, model_id="m", reported_by="r")
        self.assertEqual(usage.input_tokens, 1024)
        self.assertEqual(usage.cache_read_input_tokens, 4096)
        self.assertEqual(usage.model_id, "m")
        self.assertEqual(usage.reported_by, "r")

    def test_absent_usage_fields_parse_as_unknown_and_never_zero__negative(self):
        """Catalog sibling (§7.4 item 4) for T30.

        `entry.negative_control` names `fixtures/native/usage/coerced-zero.json`,
        the record that `usage.get("cache_read_input_tokens", 0)` turns into
        fiction. Two assertions the happy path does not make:

        1. arithmetic on an UNKNOWN raises `TypeError` **by design** -- that is
           the mechanism that makes T33 impossible to violate by accident, and
           it only works if the sentinel never silently becomes 0;
        2. a source scan of `adapters.py` for the coercion patterns, because a
           single `.get(field, 0)` reintroduced later would pass every other
           test in this file.
        """
        fixture = io.load_json(NATIVE / "usage" / "coerced-zero.json")
        usage = parse_usage(
            fixture["record"], synthetic_grammar(), model_id="m", reported_by="r"
        )
        for field in fixture["must_not_equal_zero_fields"]:
            value = getattr(usage, field)
            self.assertIs(value, UNKNOWN, field)
            self.assertNotEqual(value, 0, field)
            with self.assertRaises(TypeError, msg=f"{field} + 1 must raise, not sum"):
                _ = value + 1

        code = code_only(FRAMEWORK_DIR / "adapters.py")
        squeezed = re.sub(r"\s+", "", code)
        self.assertNotRegex(
            squeezed, r"\.get\([^)]*,0\)",
            "adapters.py must contain no '.get(name, 0)' coercion",
        )
        self.assertNotIn(
            "or0", squeezed.replace("for0", ""),
            "adapters.py must contain no 'or 0' coercion",
        )

    def test_a_reported_zero_is_distinguishable_from_an_absent_field(self):
        grammar = synthetic_grammar()
        reported = parse_usage(
            {"kind": "usage", "usage": {"output_tokens": 0}}, grammar,
            model_id="m", reported_by="r",
        )
        self.assertEqual(reported.output_tokens, 0)
        self.assertNotIn("output_tokens", reported.unknown_fields())
        absent = parse_usage({"kind": "usage", "usage": {}}, grammar, model_id="m", reported_by="r")
        self.assertIs(absent.output_tokens, UNKNOWN)
        self.assertIn("output_tokens", absent.unknown_fields())

    def test_no_grammar_is_shipped_so_load_grammar_raises(self):
        """§10.2's UNKNOWN, asserted so it cannot be filled in with a guess."""
        for name in ("claude-stream-json", "codex-exec-json"):
            with self.assertRaises(ContractError) as caught:
                load_grammar(name)
            self.assertIn("no captured harness stream exists", str(caught.exception))
        streams = adapters.STREAMS_DIR()
        self.assertEqual(
            sorted(p.name for p in streams.iterdir()), ["README.md"],
            "a *.grammar.json or a *.jsonl here would be a guessed field name",
        )


# ===========================================================================
# T31 — evidence-class labeling, with no promotion path
# ===========================================================================

class EvidenceClassLabeling(_TempMixin):
    """T31. `evidence_class_for` is the only producer, and it takes no override."""

    def test_evidence_class_is_derived_and_has_no_promotion_path(self):
        ok = ChainVerification(True, None, None, host_observed=3, caller_asserted=0, events=3)
        dirty = ChainVerification(True, None, None, host_observed=3, caller_asserted=1, events=4)
        broken = ChainVerification(False, 2, "edited-field", 3, 0, 3)

        self.assertEqual(
            evidence_class_for(AdapterClass.NATIVE, ok), EvidenceClass.NATIVE_PROVEN
        )
        self.assertEqual(
            evidence_class_for(AdapterClass.NATIVE, dirty), EvidenceClass.SIMULATED
        )
        self.assertEqual(
            evidence_class_for(AdapterClass.NATIVE, broken), EvidenceClass.SIMULATED
        )
        for chain in (ok, dirty, broken):
            self.assertEqual(
                evidence_class_for(AdapterClass.REPLAY, chain), EvidenceClass.SIMULATED
            )
            self.assertEqual(
                evidence_class_for(AdapterClass.STUB, chain), EvidenceClass.FRAMEWORK
            )

        # There is no argument, flag or config that changes the mapping.
        import inspect
        self.assertEqual(
            list(inspect.signature(evidence_class_for).parameters),
            ["adapter_class", "chain"],
        )

        # A replay cannot even be handed a host-observed ledger.
        with self.assertRaises(EvidencePromotionRefused):
            ReplaySession(
                str(REPLAY / "two-turn-acked.jsonl"), synthetic_grammar(), self.host_ledger()
            )

        # No promotion setter exists anywhere in the framework.
        for path in sorted(FRAMEWORK_DIR.glob("*.py")):
            blob = code_only(path)
            for banned in ("assume_native", "force_native", "promote_evidence"):
                self.assertNotIn(banned, blob, f"{path.name} exposes {banned}")

    def test_evidence_class_is_derived_and_has_no_promotion_path__negative(self):
        """Catalog sibling (§7.4 item 4) for T31.

        `entry.negative_control` names
        `fixtures/native/attempts/forged-native-proven.json`: an attempt that
        simply asserts `evidence_class: native-proven`, a session id no
        SESSION_ACK ever carried, and event ids that exist in no ledger. It is
        **schema-valid** -- the schema cannot see provenance -- and
        `assert_native_backed` is what refuses it. The same refusal fires when
        the event ids exist but are caller-asserted, which is the shape every
        replay produces.
        """
        raw = io.load_json(NATIVE / "attempts" / "forged-native-proven.json")
        io.load_schema("attempt").validate(raw["attempt"])   # schema-valid on purpose
        attempt = Attempt.from_dict(raw["attempt"])
        self.assertIs(attempt.evidence_class, EvidenceClass.NATIVE_PROVEN)
        self.assertTrue(attempt.claims_native)

        genuine = LedgerReader(NATIVE / "ledgers" / "genuine-caller-asserted.jsonl", key=None)
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, genuine)

        # Now with a real, verified host ledger that simply does not contain it.
        host = self.host_ledger("t31.jsonl")
        host.append(
            EventKind.SESSION_ACK, attempt_id="other", session_id="sess-other", payload={}
        )
        reader = LedgerReader(host.path, key=host.key)
        self.assertTrue(reader.is_verified())
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, reader)

        # And a replay's own caller-asserted events are refused as backing.
        ledger = self.caller_ledger("t31-replay.jsonl")
        session = ReplaySession(str(REPLAY / "two-turn-acked.jsonl"), synthetic_grammar(), ledger)
        turn = session.send("x")
        replay_reader = LedgerReader(ledger.path, key=None)
        borrowed = Attempt.from_dict(
            dict(raw["attempt"])
            | {
                "session_id": session.session_id,
                "event_ids": [turn.ack_event_id],
                "adapter_class": "replay",
            }
        )
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(borrowed, replay_reader)

    def test_native_proven_is_produced_in_exactly_one_place(self):
        """§5.4's source scan, implemented as a *producer* scan.

        The contract words this as "the literal NATIVE_PROVEN appears in exactly
        two non-test files". Taken literally that is now false and would be a
        false alarm: the landed measurement lane's `reporting.py` legitimately
        *reads* `evidence[EvidenceClass.NATIVE_PROVEN]` to implement §5.4 clause
        5. The property the contract is protecting is that nothing else
        *produces* the value, so that is what is asserted.
        """
        producers: list[str] = []
        mentions: set[str] = set()
        for path in sorted(FRAMEWORK_DIR.glob("*.py")):
            code = code_only(path)
            if "NATIVE_PROVEN" not in code:
                continue
            mentions.add(path.name)
            squeezed = re.sub(r"\s+", "", code)
            if re.search(r"(?:return|=)EvidenceClass\.NATIVE_PROVEN", squeezed):
                producers.append(path.name)
        self.assertEqual(
            sorted(set(producers)), ["adapters.py"],
            "EvidenceClass.NATIVE_PROVEN must be produced only by "
            "adapters.evidence_class_for",
        )
        self.assertIn("contract.py", mentions, "contract.py defines the member")
        self.assertLessEqual(
            mentions, {"contract.py", "adapters.py", "reporting.py"},
            "a new file mentioning NATIVE_PROVEN needs a deliberate review",
        )

    def test_the_attempt_schema_usage_block_matches_the_measurement_schema(self):
        """The inlined `usage` $def cannot drift from `usage.schema.json`."""
        attempt = json.loads((REPO / "evals/agentic/schemas/attempt.schema.json").read_text())
        usage = json.loads((REPO / "evals/agentic/schemas/usage.schema.json").read_text())
        inlined = attempt["$defs"]["usage"]
        self.assertEqual(sorted(inlined["required"]), sorted(usage["required"]))
        self.assertEqual(sorted(inlined["properties"]), sorted(usage["properties"]))
        self.assertEqual(
            attempt["$defs"]["token_count"]["oneOf"], usage["$defs"]["token_count"]["oneOf"]
        )


# ===========================================================================
# Catalog self-consistency (this lane's fragment)
# ===========================================================================

class AdapterCatalogFragment(unittest.TestCase):
    """Every §7.3/§7.4 rule this lane can check without the integration runner."""

    def test_fragment_is_well_formed_and_every_entry_resolves(self):
        fragment = io.load_json(REPO / "evals/agentic/manifests/catalog/adapter.json")
        self.assertEqual(fragment["lane"], "adapter")
        ids = [e["id"] for e in fragment["entries"]]
        self.assertEqual(ids, ["T25", "T26", "T27", "T28", "T29", "T30", "T31"])

        gated = {e["id"] for e in fragment["entries"] if e["approval_gate"] != "none"}
        self.assertEqual(
            gated, {"T26", "T27", "T28", "T29"},
            "§7.4 item 5 names exactly these four as native-required",
        )
        for entry in fragment["entries"]:
            with self.subTest(entry=entry["id"]):
                if entry["id"] in gated:
                    self.assertEqual(entry["approval_gate"], "native-required")
                module = __import__(entry["module"], fromlist=["*"])
                klass = getattr(module, entry["test_class"])
                self.assertTrue(hasattr(klass, entry["test_name"]))
                self.assertTrue(
                    hasattr(klass, entry["test_name"] + "__negative"),
                    f"{entry['id']} has no executable negative control sibling",
                )
                method = getattr(klass, entry["test_name"])
                self.assertFalse(
                    getattr(method, "__unittest_skip__", False), f"{entry['id']} is skipped"
                )
                self.assertTrue(
                    (REPO / entry["negative_control"]).exists(),
                    f"{entry['id']} negative_control does not resolve: "
                    f"{entry['negative_control']}",
                )

    def test_gated_entries_are_named_offline_form(self):
        fragment = io.load_json(REPO / "evals/agentic/manifests/catalog/adapter.json")
        for entry in fragment["entries"]:
            if entry["approval_gate"] == "native-required":
                self.assertTrue(
                    entry["test_name"].endswith("__offline_form"),
                    f"{entry['id']}: §10.5 item 5 requires the offline form to be named "
                    "so no reader mistakes it for closure",
                )
                self.assertEqual(entry["evidence_class"], "simulated")


if __name__ == "__main__":
    unittest.main()
