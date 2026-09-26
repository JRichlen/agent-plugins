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

import dataclasses
import hashlib
import hmac
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
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
from evals.agentic.framework.classify import RunFacts
from evals.agentic.framework.contract import (
    UNKNOWN,
    ApprovalRequired,
    ArmRole,
    Attempt,
    ContractError,
    EvidenceClass,
    EvidencePromotionRefused,
    EventKind,
    FlagNotSupported,
    ForgedProvenance,
    Manifest,
    SignatureClass,
    Stratum,
    TerminalState,
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

    REPAIR N-11: `allow` names argv tuples this particular block is willing to
    see spawned, and it is the ONLY relaxation -- every other argv still reds
    the test at construction, and `permitted` records what actually ran so a
    caller can assert the allowance was *used* rather than merely tolerated.
    `adapters.dry_run` now validates the driver's flags against the installed
    binary's own `--help` before it renders anything (that is the whole point
    of the repair: a plausible argv must never be printed unvalidated), so a
    blanket "no Popen at all" would be asserting the absence of the check.
    What matters -- and what the allowance keeps exact -- is that the *planned
    argv* is never the thing executed.
    """

    def __init__(
        self, case: unittest.TestCase, *, allow: "Sequence[Sequence[str]] | None" = None
    ) -> None:
        self.case = case
        self.calls: list[tuple] = []
        self.permitted: list[tuple[str, ...]] = []
        self._allow = {tuple(a) for a in (allow or ())}
        self._real = subprocess.Popen

    def __enter__(self) -> "_NoSpawn":
        outer = self

        class _Trap(outer._real):  # type: ignore[misc, valid-type]
            def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
                argv = tuple(args[0]) if args and isinstance(args[0], (list, tuple)) else ()
                if argv in outer._allow:
                    outer.permitted.append(argv)
                    super().__init__(*args, **kwargs)
                    return
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

    #: REPAIR F1: the catalog entry (T25) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/agentic/fixtures/native/drivers/invented-flag.json"

    def test_driver_flags_conform_to_installed_help_and_spawn_needs_approval(self):
        """The catalog anchor for T25. Runs both installed CLIs' help for real."""
        checked = 0
        for name in ("claude", "codex"):
            config = load_driver_config(name)
            self.assertTrue(os.path.isabs(config.binary), f"{name}: binary must be absolute")
            self.assertTrue(os.path.isfile(config.binary), f"{name}: binary must exist")

            help_text = installed_help(config)
            self.assertGreater(
                len(help_text), 200,
                f"{name}: --help produced nothing usable ({len(help_text)} chars): {help_text[:300]!r}",
            )

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

    def test_control_configs_resolve_by_declared_binary_basename_on_a_foreign_host(self):
        """A control config (invented-flag, dangerous-flag) declares the real claude
        binary under a different config NAME. On a host where the committed absolute
        path does not exist (CI, a reinstall) the loader must fall back by the
        declared binary's basename, not by the config name -- otherwise the
        negative controls cannot even load there and T25's sibling executes
        nothing (observed on the GitHub runner, 2026-09-07)."""
        import json as _json, tempfile as _tempfile, pathlib as _pathlib
        from evals.agentic.framework.adapters import DRIVERS_DIR
        real = load_driver_config("claude")
        src = _json.loads((DRIVERS_DIR() / "invented-flag.json").read_text())
        src["binary"] = "/nonexistent/host/path/bin/claude"
        with _tempfile.TemporaryDirectory() as tmp:
            alt = _pathlib.Path(tmp) / "drivers"
            alt.mkdir()
            (alt / "invented-flag.json").write_text(_json.dumps(src))
            import evals.agentic.framework.adapters as _ad
            saved = _ad.DRIVERS_DIR
            try:
                _ad.DRIVERS_DIR = lambda: alt
                cfg = load_driver_config("invented-flag")
            finally:
                _ad.DRIVERS_DIR = saved
        self.assertTrue(os.path.isabs(cfg.binary))
        self.assertEqual(os.path.basename(cfg.binary), "claude")
        self.assertEqual(os.path.realpath(cfg.binary), os.path.realpath(real.binary))

    def test_control_configs_resolve_by_declared_binary_basename_on_a_foreign_host__negative(self):
        """A basename that is installed nowhere must still fail closed."""
        import json as _json, tempfile as _tempfile, pathlib as _pathlib
        from evals.agentic.framework.adapters import DRIVERS_DIR
        src = _json.loads((DRIVERS_DIR() / "invented-flag.json").read_text())
        src["binary"] = "/nonexistent/host/path/bin/no-such-cli-xyz"
        with _tempfile.TemporaryDirectory() as tmp:
            alt = _pathlib.Path(tmp) / "drivers"
            alt.mkdir()
            (alt / "invented-flag.json").write_text(_json.dumps(src))
            import evals.agentic.framework.adapters as _ad
            saved = _ad.DRIVERS_DIR
            try:
                _ad.DRIVERS_DIR = lambda: alt
                with self.assertRaises(ContractError):
                    load_driver_config("invented-flag")
            finally:
                _ad.DRIVERS_DIR = saved

    def test_bypass_permissions_mode_is_banned_by_value_not_by_flag_spelling(self):
        """The handoff bans the *mode*; neither CLI spells it as a flag.

        `BANNED_FLAG_PATTERNS` matches `^--dangerously-` / `^--allow-dangerously-`
        and `declared_flags` only yields tokens beginning with `-`, so the ban
        used to be a ban on two spellings. The installed CLIs' real bypass
        surfaces are VALUES in free-text slots -- `claude --permission-mode
        bypassPermissions` and `codex exec --sandbox danger-full-access` -- and a
        scan for flag names cannot see either one.

        Both surfaces are covered here, because they fail at different times:
        the config document (what a future edit touches) and the rendered argv
        (what a caller reaches through a `{slot}` at run time).
        """
        # 1. The config document.
        for name, flag in (
            ("bypass-value", "--permission-mode"),
            ("bypass-sandbox-value", "--sandbox"),
        ):
            with self.subTest(config=name):
                config = load_driver_config(name)
                self.assertEqual(
                    declared_flags(config).count("--dangerously-skip-permissions"), 0,
                    "no banned FLAG appears here -- that is the point of the fixture",
                )
                with _NoSpawn(self) as trap:
                    with self.assertRaises(FlagNotSupported) as caught:
                        assert_flags_supported(config)
                self.assertEqual(
                    trap.calls, [],
                    "a banned value must be refused before the installed help is consulted",
                )
                self.assertEqual(getattr(caught.exception, "flag", None), flag)

        # 2. The rendered argv, i.e. the call-time slot the shipped configs have.
        for name, slot, value in (
            ("claude", "permission_mode", "bypassPermissions"),
            ("codex", "sandbox", "danger-full-access"),
        ):
            driver = CliDriver(load_driver_config(name))
            for spelling in (value, value.upper(), value.replace("-", "_")):
                with self.subTest(driver=name, value=spelling):
                    slots = dict(adapters._DEFAULT_SLOTS[name]["fresh"])
                    slots[slot] = spelling
                    with _NoSpawn(self):
                        with self.assertRaises(FlagNotSupported) as caught:
                            driver.build_argv(mode="fresh", **slots)
                    self.assertIn("bypass-permissions mode", str(caught.exception))

        # 3. An unrecognised value for a bypass surface is refused too: these
        #    two slots take an allowlist, so a CLI that renames or adds a bypass
        #    mode reds this instead of passing through a stale ban list.
        driver = CliDriver(load_driver_config("codex"))
        slots = dict(adapters._DEFAULT_SLOTS["codex"]["fresh"])
        slots["sandbox"] = "full-access-but-spelled-differently"
        with self.assertRaises(FlagNotSupported) as caught:
            driver.build_argv(mode="fresh", **slots)
        self.assertIn("allowlist", str(caught.exception))

        # 4. And the env is the third way into the same mode.
        with self.assertRaises(FlagNotSupported):
            adapters._resolve_env(
                DriverConfig(
                    name="env-bypass", binary="/bin/true", help_argv=("--help",),
                    argv_template=(), optional_argv={"fresh": ()},
                    env={"CLAUDE_PERMISSION_MODE": "{mode}"}, cwd="/w", timeout_s=1.0,
                    stream_format="jsonl", grammar="g", adapter_class=AdapterClass.NATIVE,
                ),
                {"mode": "bypassPermissions"},
            )

    def test_bypass_permissions_mode_is_banned_by_value_not_by_flag_spelling__negative(self):
        """The control has to still let the honest values through.

        A "refuse every value" rule passes the test above and makes the driver
        unusable, and a check wired only into `assert_flags_supported` passes it
        for the config while leaving every call-time slot open. Both are
        asserted against here: the shipped configs conform, every allowlisted
        value builds, and `dry_run` -- which is the path §8.5's acceptance
        prints -- renders a real safe value rather than a placeholder that had
        to be exempted from the check.
        """
        for name in ("claude", "codex"):
            with self.subTest(driver=name):
                config = load_driver_config(name)
                for tokens in (
                    config.argv_template,
                    *(config.optional_argv[m] for m in sorted(config.optional_argv)),
                ):
                    adapters._assert_argv_values_allowed(
                        tokens, driver=name, where="test",
                    )   # must not raise: the shipped documents are conformant

        driver = CliDriver(load_driver_config("claude"))
        for mode in sorted(adapters.SAFE_ARGV_VALUES["--permission-mode"]):
            with self.subTest(permission_mode=mode):
                slots = dict(adapters._DEFAULT_SLOTS["claude"]["fresh"])
                slots["permission_mode"] = mode
                self.assertIn(mode, driver.build_argv(mode="fresh", **slots))

        codex = CliDriver(load_driver_config("codex"))
        for sandbox in sorted(adapters.SAFE_ARGV_VALUES["--sandbox"]):
            with self.subTest(sandbox=sandbox):
                slots = dict(adapters._DEFAULT_SLOTS["codex"]["fresh"])
                slots["sandbox"] = sandbox
                self.assertIn(sandbox, codex.build_argv(mode="fresh", **slots))

        rendered = dry_run("claude")
        self.assertIn("--permission-mode plan", rendered)
        self.assertNotIn(
            "<permission-mode>", rendered,
            "a dry run that renders an unchecked placeholder into a bypass slot is a dry "
            "run of different argv than a real spawn builds",
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
        # The same scan at the VALUE level. A flag-spelling scan reads clean on
        # a config that says `"--permission-mode", "bypassPermissions"`, which
        # is the shape the installed CLIs actually accept.
        for name in ("claude", "codex"):
            blob = (adapters.DRIVERS_DIR() / f"{name}.json").read_text(encoding="utf-8")
            for banned in ("bypassPermissions", "danger-full-access"):
                self.assertNotIn(banned, blob, f"{name}: {banned} is a banned VALUE")

    def test_dry_run_prints_planned_argv_and_never_spawns(self):
        """The §8.5 acceptance text, asserted rather than eyeballed.

        REPAIR N-11: `dry_run` now runs `assert_flags_supported` against the
        INSTALLED binary before rendering, so exactly one child is expected --
        `binary + help_argv` -- and nothing else. The assertion is therefore
        sharper than the old blanket "no Popen": the help invocation must
        happen (else the printed argv is unvalidated), and the *planned argv*
        must never be executed.
        """
        for name in ("claude", "codex"):
            config = load_driver_config(name)
            help_argv = (config.binary, *config.help_argv)
            with _NoSpawn(self, allow=[help_argv]) as trap:
                rendered = dry_run(name)
            self.assertEqual(trap.calls, [], f"{name}: an unexpected child was spawned")
            self.assertEqual(
                trap.permitted, [help_argv],
                f"{name}: dry_run must validate flags against the installed help exactly once",
            )
            self.assertIn("argv: ", rendered)
            self.assertIn(
                f"flags: validated against the installed {config.binary} "
                f"{' '.join(config.help_argv)} output",
                rendered, name,
            )
            self.assertIn(
                "adapter_class=native (NOT SPAWNED — no approval token)", rendered, name
            )
            # The planned argv itself is never what ran.
            planned_line = next(l for l in rendered.splitlines() if l.startswith("argv: "))
            self.assertNotEqual(
                tuple(planned_line[len("argv: "):].split()), help_argv,
                f"{name}: the planned invocation must not be the help invocation",
            )

    def test_dry_run_prints_planned_argv_and_never_spawns__negative(self):
        """REPAIR N-11's own negative control: a driver whose template names a
        flag the installed CLI does not list must be REFUSED by `dry_run`, not
        rendered anyway.

        `fixtures/native/drivers/invented-flag.json` is the shipped artifact
        for exactly this (it is T25's `negative_control`): a config identical
        to the real `claude` one but carrying `--session-name`, which the
        installed CLI's help does not list. Before this repair `dry_run`
        happily printed a copy-pasteable command line containing it.
        """
        invented = load_driver_config("invented-flag")
        self.assertIn(
            "--session-name", declared_flags(invented),
            "the fixture must still be the invented-flag control",
        )
        # The pure renderer is perfectly happy with it -- which is the defect.
        argv = CliDriver(invented).build_argv(
            session_name="s", workspace="/w", home="/h",
        )
        self.assertIn("--session-name", argv)
        # `dry_run` is not: it consults the installed help first and refuses.
        with self.assertRaises(FlagNotSupported) as caught:
            dry_run("invented-flag")
        self.assertIn("--session-name", str(caught.exception))
        self.assertEqual(getattr(caught.exception, "flag", None), "--session-name")

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

    #: REPAIR F1: the catalog entry (T26) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/agentic/fixtures/native/replay/no-session-ack.jsonl"

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

    #: REPAIR F1: the catalog entry (T27) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/agentic/fixtures/native/isolation/carried-over"

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

    #: REPAIR F1: the catalog entry (T28) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/agentic/fixtures/native/workers/worker_ignores_sigterm.py"

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

    #: REPAIR F1: the catalog entry (T29) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/agentic/fixtures/native/tamper/edited-field.jsonl"

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

        # A ledger of EITHER witness mints or refuses its own key; a supplied
        # one is refused, because supplying the key is becoming the host.
        for witness in (SignatureClass.HOST_OBSERVED, SignatureClass.CALLER_ASSERTED):
            with self.subTest(witness=witness):
                with self.assertRaises(EvidencePromotionRefused):
                    HostLedger(
                        self.tmp / f"supplied-{witness.value}.jsonl", run_id="r",
                        witness=witness, key=b"\x00" * 32,
                    )
        host = self.host_ledger()
        ack = host.append(
            EventKind.SESSION_ACK, attempt_id="a1", session_id="sess-real",
            payload={"source": "harness"},
        )
        reader = host.verifier()
        self.assertTrue(reader.verify_chain().ok)
        self.assertIsNone(reader.verification_reason())
        self.assertTrue(reader.is_verified())
        self.assertEqual(reader.host_observed_session_ids(), frozenset({"sess-real"}))
        self.assertEqual(reader.signature_class(ack.event_id), SignatureClass.HOST_OBSERVED)
        # `key=host.key` is the same capability by another name.
        self.assertTrue(LedgerReader(host.path, key=host.key).is_verified())

        # The key is never written anywhere in the workspace.
        blob = host.path.read_bytes()
        self.assertNotIn(adapters._run_key_bytes(host.key), blob)
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

    def test_a_verifier_cannot_be_handed_a_key_of_its_own_choosing(self):
        """The key is a capability, not a parameter (§5.3).

        The forgery this refuses needs no source edit, no commit access and no
        access to any real run key: hand-type a ledger whose entries declare
        `value_class: host-observed`, HMAC each one under a key you picked, then
        ask a `LedgerReader` to verify it *with that key*. Every check downstream
        agreed -- `verify_chain().ok`, `is_verified()`, `host_observed_session_ids()`
        and therefore `contract.assert_native_backed` -- because `_signature_ok`
        recomputed the HMAC under whatever bytes the caller passed in.

        Whoever chooses the key is the host. So the key cannot be chosen: the
        only thing that blesses is the `_RunKey` `HostLedger.verifier()` wraps,
        and it is bound to the path of the ledger that minted it.
        """
        host = self.host_ledger("capability.jsonl")
        host.append(
            EventKind.SESSION_ACK, attempt_id="a", session_id="sess-real", payload={}
        )
        host.close()

        # 1. Raw bytes are refused outright, including the real key's own bytes
        #    laundered back into the public parameter.
        for label, raw in (
            ("attacker-chosen", b"attacker-chosen-key-32-bytes!!!!"),
            ("the-real-bytes", adapters._run_key_bytes(host.key)),
        ):
            with self.subTest(key=label), self.assertRaises(EvidencePromotionRefused) as cm:
                LedgerReader(host.path, key=raw)
            self.assertIn("raw key is refused", str(cm.exception))

        # 2. Hand-type a ledger, sign it under a key of your own, and there is
        #    no reader you are allowed to build that will bless it.
        forged = self.tmp / "forged.jsonl"
        key = b"attacker-chosen-key-32-bytes!!!!"
        prev = "0" * 64
        lines: list[str] = []
        for index, kind in enumerate((EventKind.SESSION_OPEN, EventKind.SESSION_ACK)):
            body = {
                "index": index, "event_id": str(uuid.uuid4()), "run_id": "run-forged",
                "attempt_id": "attempt-forged",
                "session_id": "harness-sess-TOTALLY-FAKE" if index else None,
                "kind": kind.value, "at": "2026-09-06T12:00:00.000Z",
                "payload": {"source": "typed by hand"}, "prev_hash": prev,
                "host_signature": {
                    "value_class": "host-observed", "algo": "hmac-sha256",
                    "key_id": "run-forged",
                },
            }
            message = adapters._chain_message(prev, body)
            record = dict(body)
            record["sha256"] = hashlib.sha256(message).hexdigest()
            record["host_signature"] = dict(body["host_signature"]) | {
                "value": hmac.new(key, message, hashlib.sha256).hexdigest()
            }
            prev = record["sha256"]
            lines.append(json.dumps(record, sort_keys=True, separators=(",", ":")))
        forged.write_text("\n".join(lines) + "\n", encoding="utf-8")

        with self.assertRaises(EvidencePromotionRefused):
            LedgerReader(forged, key=key)
        blind = LedgerReader(forged, key=None)
        self.assertTrue(
            blind.verify_chain().ok,
            "the forger relinked the chain -- the chain was never the gate",
        )
        self.assertFalse(blind.is_verified())
        self.assertEqual(
            blind.verification_reason(), LedgerReader.UNVERIFIABLE_IN_THIS_PROCESS
        )

        # 3. Nor by borrowing a capability minted for a DIFFERENT ledger: a
        #    throwaway host ledger is free to construct, so the capability has
        #    to be bound to the file it was minted over.
        throwaway = self.host_ledger("throwaway.jsonl")
        with self.assertRaises(EvidencePromotionRefused) as cm:
            LedgerReader(forged, key=throwaway.key)
        self.assertIn("was minted for", str(cm.exception))

    def test_a_verifier_cannot_be_handed_a_key_of_its_own_choosing__negative(self):
        """The vacuous blessings the capability alone does not stop.

        Two ledgers that a "chain is intact AND a key was supplied" rule calls
        verified while the host witnessed nothing at all:

        1. an all-caller-asserted ledger -- `_signature_ok` short-circuits True
           for every caller-asserted entry, so the key is never used and the
           verdict reduces to "this replay's chain is intact";
        2. an EMPTY host-observed ledger -- `ok`, no caller-asserted entries,
           a real capability, and nothing whatsoever behind it. This one also
           reached `evidence_class_for`, which called it NATIVE_PROVEN.

        `reporting.assert_native_claims` clause 2 trusts `is_verified()`, so
        either one was a report printing native sentences over a run in which no
        harness ever ran.
        """
        replay = self.caller_ledger("vacuous-replay.jsonl")
        replay.append(
            EventKind.SESSION_ACK, attempt_id="a", session_id="sess-replayed", payload={}
        )
        replay.close()
        reader = replay.verifier()
        self.assertTrue(reader.verify_chain().ok)
        self.assertFalse(
            reader.is_verified(),
            "a ledger in which the host witnessed nothing is not 'verified'",
        )
        self.assertEqual(
            reader.host_observed_session_ids(), frozenset(),
            "and it blesses no session id either",
        )

        empty = self.host_ledger("vacuous-empty.jsonl")
        empty.close()
        chain = empty.verifier().verify_chain()
        self.assertEqual((chain.ok, chain.events, chain.host_observed), (True, 0, 0))
        self.assertFalse(
            empty.verifier().is_verified(),
            "an empty ledger satisfies every structural check and proves nothing",
        )
        self.assertIn("witnessed nothing", empty.verifier().verification_reason() or "")
        self.assertEqual(
            evidence_class_for(AdapterClass.NATIVE, chain), EvidenceClass.SIMULATED,
            "an empty chain must not be the framework's strongest evidence class",
        )

    def test_the_witness_and_the_key_are_sealed_against_post_construction_flips(self):
        """§10.5 item 3 against the cheapest laundering there is.

        `HostLedger`'s witness used to be an ordinary attribute that `append()`
        re-read on every call, while `ReplaySession` checked it only once, at
        construction. So: build a legal caller-asserted ledger, hand it to a
        `ReplaySession` (which accepts it), then assign
        `ledger._witness = HOST_OBSERVED` and `ledger._key = <bytes>`. Every
        subsequent entry was minted host-observed, correctly HMAC'd under a key
        the forger chose, and the replay was laundered whole -- with no source
        edit, i.e. strictly cheaper than counterfeit fixture 23(b).

        Two independent mechanisms now refuse it, and this test asserts both.
        """
        ledger = self.caller_ledger("sealed.jsonl")
        session = ReplaySession(
            str(REPLAY / "two-turn-acked.jsonl"), synthetic_grammar(), ledger
        )
        self.assertIsNotNone(session.session_id)

        # 1. The attributes cannot be rebound, and the refusal names the reason.
        for name, value in (
            ("_witness", SignatureClass.HOST_OBSERVED),
            ("_key", b"\x01" * 32),
            ("_stamp", lambda message=None: {"value_class": "host-observed"}),
            ("_witness_of", lambda: SignatureClass.HOST_OBSERVED),
            ("_run_key", None),
            ("_sealed", False),
        ):
            with self.subTest(attribute=name):
                with self.assertRaises(EvidencePromotionRefused) as cm:
                    setattr(ledger, name, value)
                self.assertIn("sealed at construction", str(cm.exception))
                with self.assertRaises(EvidencePromotionRefused):
                    delattr(ledger, name)

        # 2. Even reaching past __setattr__ changes nothing: the witness and the
        #    key live in a closure, so there is no attribute for append() to read.
        with self.assertRaises(AttributeError):
            object.__setattr__(ledger, "_witness", SignatureClass.HOST_OBSERVED)
        self.assertIs(ledger.witness, SignatureClass.CALLER_ASSERTED)
        session.send("laundered")
        event = ledger.append(
            EventKind.SESSION_ACK, attempt_id="attempt-flip",
            session_id=session.session_id, payload={"source": "laundered"},
        )
        ledger.close()

        reader = ledger.verifier()
        self.assertFalse(reader.is_verified())
        self.assertEqual(reader.host_observed_session_ids(), frozenset())
        self.assertEqual(
            reader.signature_class(event.event_id), SignatureClass.CALLER_ASSERTED
        )
        self.assertTrue(
            all(
                r["host_signature"]["value_class"] == SignatureClass.CALLER_ASSERTED.value
                and r["host_signature"]["value"] is None
                for r in reader.records()
            ),
            "every entry a replay ledger writes stays caller-asserted, whatever was flipped",
        )

    def test_the_witness_and_the_key_are_sealed_against_post_construction_flips__negative(self):
        """The write cursor MUST stay mutable, or the seal is not a seal but a freeze.

        A guard that refuses every assignment passes the test above while
        breaking `append()` on its second call. The seal has to be exactly as
        wide as the identity of the ledger and no wider.
        """
        ledger = self.host_ledger("seal-width.jsonl")
        first = ledger.append(EventKind.RUN_START, attempt_id=None, session_id=None, payload={})
        second = ledger.append(EventKind.RUN_END, attempt_id=None, session_id=None, payload={})
        ledger.close()
        self.assertNotEqual(first.event_id, second.event_id)
        reader = ledger.verifier()
        self.assertTrue(reader.is_verified(), "a sealed ledger must still be writable")
        self.assertEqual([r["index"] for r in reader.records()], [0, 1])

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

    #: REPAIR F1: the catalog entry (T30) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/agentic/fixtures/native/usage/coerced-zero.json"

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

    def test_a_grammar_exists_only_for_a_cli_whose_stream_was_captured(self):
        """§10.2's UNKNOWN, settled PER DRIVER by capture and by nothing else.

        `claude` was driven live on 2026-09-07 under approval token
        `user-approved-2026-09-07-native`, so its grammar exists and every path
        in it was read off `streams/claude-2026-09-07.jsonl`. `codex` was not
        driven, so `load_grammar` still raises for it -- which is the whole
        point: the presence of a grammar is evidence that a capture happened,
        not a convention someone can satisfy by typing field names.
        """
        grammar = load_grammar("claude-stream-json")
        self.assertEqual(grammar.captured_from, "claude-2026-09-07.jsonl")
        capture = adapters.STREAMS_DIR() / grammar.captured_from
        self.assertTrue(capture.is_file())

        # Every match/extract path must actually fire on the capture it claims
        # to come from. A grammar that parses its own capture into silence is
        # exactly the silent-degradation failure §10.2 warns about.
        records = list(io.read_jsonl(capture))
        self.assertGreaterEqual(len(records), 5)
        acks = [r for r in records if grammar.session_ack.matches(r)]
        turns = [r for r in records if grammar.turn_ack.matches(r)]
        usages = [r for r in records if grammar.usage.matches(r)]
        self.assertEqual(len(acks), 1, "exactly one session ack in a one-turn capture")
        self.assertGreaterEqual(len(turns), 1)
        self.assertEqual(len(usages), 1)
        sid = grammar.session_ack.extracted(acks[0]).get(grammar.session_id_field)
        self.assertIsInstance(sid, str)
        self.assertTrue(sid)

        # An absent field stays absent. The capture shows the CLI reporting no
        # total token count at all, so it must read UNKNOWN, never 0 (§10.4).
        usage = parse_usage(usages[0], grammar, model_id="m", reported_by="capture")
        self.assertIs(usage.total_tokens, UNKNOWN)
        self.assertIsNot(usage.input_tokens, UNKNOWN)

        # codex: no capture, therefore no grammar, therefore a refusal.
        with self.assertRaises(ContractError) as caught:
            load_grammar("codex-exec-json")
        self.assertIn("no captured harness stream exists", str(caught.exception))
        self.assertFalse((adapters.GRAMMARS_DIR() / "codex-exec-json.json").exists())

    def test_a_grammar_whose_capture_is_missing_is_refused(self):
        """The binding is checked, not declared: delete the capture and the
        grammar stops loading. Without this, `captured_from` is a comment."""
        import shutil as _shutil
        real = adapters.GRAMMARS_DIR() / "claude-stream-json.json"
        doc = json.loads(real.read_text(encoding="utf-8"))
        doc["captured_from"] = "claude-1999-01-01-does-not-exist.jsonl"
        alt = self.tmp / "grammars"
        alt.mkdir()
        (alt / "claude-stream-json.json").write_text(json.dumps(doc), encoding="utf-8")
        saved = adapters.GRAMMARS_DIR
        try:
            adapters.GRAMMARS_DIR = lambda: alt
            with self.assertRaises(ContractError) as caught:
                load_grammar("claude-stream-json")
        finally:
            adapters.GRAMMARS_DIR = saved
        self.assertIn("does not exist", str(caught.exception))
        del _shutil


# ===========================================================================
# T31 — evidence-class labeling, with no promotion path
# ===========================================================================

class EvidenceClassLabeling(_TempMixin):
    """T31. `evidence_class_for` is the only producer, and it takes no override."""

    #: REPAIR F1: the catalog entry (T31) this class answers, declared so
    #: `run.py --catalog` can BIND manifests/catalog/*.json's negative_control
    #: field to this test rather than checking the two independently.
    negative_control = "evals/agentic/fixtures/native/attempts/forged-native-proven.json"

    def test_evidence_class_is_derived_and_has_no_promotion_path(self):
        ok = ChainVerification(True, None, None, host_observed=3, caller_asserted=0, events=3)
        dirty = ChainVerification(True, None, None, host_observed=3, caller_asserted=1, events=4)
        broken = ChainVerification(False, 2, "edited-field", 3, 0, 3)
        # A ledger nobody ever wrote to: intact, no caller-asserted entries, and
        # no evidence of anything. It satisfies every structural clause.
        vacuous = ChainVerification(True, None, None, host_observed=0, caller_asserted=0, events=0)

        self.assertEqual(
            evidence_class_for(AdapterClass.NATIVE, ok), EvidenceClass.NATIVE_PROVEN
        )
        self.assertEqual(
            evidence_class_for(AdapterClass.NATIVE, dirty), EvidenceClass.SIMULATED
        )
        self.assertEqual(
            evidence_class_for(AdapterClass.NATIVE, broken), EvidenceClass.SIMULATED
        )
        self.assertEqual(
            evidence_class_for(AdapterClass.NATIVE, vacuous), EvidenceClass.SIMULATED,
            "an empty chain must not be the framework's strongest evidence class",
        )
        for chain in (ok, dirty, broken, vacuous):
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


# ===========================================================================
# REPAIR S-12 — attempt_from_session: the production session -> Attempt seam
# REPAIR S-10 — LedgerReader.spawn_exit_accounting: the external witness
# ===========================================================================

def _stratum() -> Stratum:
    return Stratum(provider="anthropic", model="claude-sonnet-5", revision="r1",
                   effort="high", harness="claude-code/1.0")


def _delivered_facts() -> RunFacts:
    return RunFacts(
        exit_status=0, signalled=None, deliverable_present=True, verifier_verdict=True,
        verifier_green_at_ms=100, cancel_issued_at_ms=None, wall_clock_ms=200,
        wall_clock_limit_ms=1000, transport_error=None, bytes_out=42,
    )


class AttemptFromSession(_TempMixin):
    """REPAIR S-12. A real Attempt built from a live session, offline.

    Before this seam existed, every `Attempt` in the tree was hand-built by a
    test or a fixture builder: nothing a driver produced could reach
    `accounting.AttemptLedger`/`reporting.build_report`, and `classify()` had
    no production caller at all.
    """

    def _replay_session(self, stream: str = "two-turn-acked.jsonl", **kw):
        ledger = self.caller_ledger(f"replay-{stream}")
        return ReplaySession(str(REPLAY / stream), synthetic_grammar(), ledger, **kw)

    def test_attempt_from_a_replay_session_is_simulated_and_makes_no_native_claim(self):
        session = self._replay_session(attempt_id="attempt-s12-replay")
        session.send("hello")
        session.send("again")
        # The replayed stream DOES carry a session ack -- that is the trap.
        self.assertEqual(session.session_id, "harness-sess-AAAA")

        attempt = adapters.attempt_from_session(
            session, card_id="graveyard-pos-01", arm_id="arm-full",
            role=ArmRole.TREATMENT, facts=_delivered_facts(),
            requested=_stratum(), realized=_stratum(), attempt_id="attempt-s12-replay",
        )

        self.assertEqual(attempt.adapter_class, AdapterClass.REPLAY)
        self.assertEqual(attempt.evidence_class, EvidenceClass.SIMULATED)
        self.assertNotEqual(attempt.evidence_class, EvidenceClass.NATIVE_PROVEN)
        self.assertEqual(attempt.terminal_state, TerminalState.DELIVERED)
        # The ack came out of a FILE. It is recorded, weightless, and NOT
        # copied onto the attempt, where it would make a simulated row claim
        # native provenance and be refused by assert_native_backed.
        self.assertIsNone(attempt.session_id)
        self.assertEqual(attempt.event_ids, ())
        self.assertFalse(attempt.claims_native)
        self.assertIn("harness-sess-AAAA", attempt.notes)
        self.assertIn("evidence=simulated", attempt.notes)

        # It is a REAL Attempt: schema-valid, and it survives the native gate.
        io.load_schema("attempt").validate(attempt.to_dict())
        assert_native_backed(attempt, LedgerReader(session.ledger.path, key=None))
        self.assertEqual(Attempt.from_dict(attempt.to_dict()), attempt)

    def test_attempt_from_a_real_worker_session_is_real_fixture_never_native(self):
        pool = protocols.WorkerPool(cwd=self.tmp, timeout_s=20.0)
        self.addCleanup(pool.close)
        pool.spawn("w1", ["python3", "-c", "print('done')"])
        pool.collect()
        session = attach_session(
            ledger=self.caller_ledger("worker.jsonl"), adapter_class=AdapterClass.STUB,
            pool=pool, worker_id="w1", attempt_id="attempt-s12-worker",
        )
        self.addCleanup(session.close)
        self.assertTrue(session.backed_by_real_process)

        attempt = adapters.attempt_from_session(
            session, card_id="voice-pos-01", arm_id="arm-baseline",
            role=ArmRole.BASELINE, facts=_delivered_facts(),
            requested=_stratum(), realized=_stratum(), attempt_id="attempt-s12-worker",
        )
        # A real subprocess is not a harness (§10.5): REAL_FIXTURE, never NATIVE_PROVEN.
        self.assertEqual(attempt.evidence_class, EvidenceClass.REAL_FIXTURE)
        self.assertEqual(attempt.adapter_class, AdapterClass.STUB)
        self.assertIsNone(attempt.session_id)
        self.assertFalse(attempt.claims_native)
        io.load_schema("attempt").validate(attempt.to_dict())

    def test_classifier_is_consulted_not_a_terminal_state_parameter(self):
        """`terminal_state` is DERIVED. There is no parameter to hand it in,
        and a different fact pattern produces a different state from the same
        session."""
        import inspect as _inspect

        signature = _inspect.signature(adapters.attempt_from_session)
        for banned in ("terminal_state", "evidence_class", "adapter_class"):
            self.assertNotIn(
                banned, signature.parameters,
                f"attempt_from_session must DERIVE {banned}, never accept it",
            )

        cancelled_facts = RunFacts(
            exit_status=None, signalled="SIGKILL", deliverable_present=False,
            verifier_verdict=None, verifier_green_at_ms=None, cancel_issued_at_ms=50,
            wall_clock_ms=80, wall_clock_limit_ms=1000, transport_error=None, bytes_out=3,
        )
        session = self._replay_session(attempt_id="attempt-s12-cancel")
        attempt = adapters.attempt_from_session(
            session, card_id="voice-neg-02", arm_id="arm-full", role=ArmRole.TREATMENT,
            facts=cancelled_facts, requested=_stratum(), realized=_stratum(),
            attempt_id="attempt-s12-cancel",
        )
        self.assertEqual(attempt.terminal_state, TerminalState.CANCELLED)
        self.assertFalse(attempt.scoring_valid)

    def test_attempt_from_a_replay_session_is_simulated_and_makes_no_native_claim__negative(self):
        """The control: this constructor must have NO promotion path.

        Three attacks, all of which the seam has to refuse rather than
        launder: a caller-chosen evidence class (there is no such keyword),
        a replay session holding a host-observed ledger, and a hand-edited
        attempt document that pairs `native-proven` with `adapter_class:
        replay` -- the exact splice the S-12 constructor could otherwise be
        used to legitimise.
        """
        session = self._replay_session(attempt_id="attempt-s12-neg")
        with self.assertRaises(TypeError):
            adapters.attempt_from_session(  # type: ignore[call-arg]
                session, card_id="c", arm_id="a", role=ArmRole.TREATMENT,
                facts=_delivered_facts(), requested=_stratum(), realized=_stratum(),
                evidence_class=EvidenceClass.NATIVE_PROVEN,
            )

        # A replay cannot even be given a host-observed ledger to start from.
        with self.assertRaises(EvidencePromotionRefused):
            ReplaySession(
                str(REPLAY / "two-turn-acked.jsonl"), synthetic_grammar(),
                self.host_ledger("promote.jsonl"),
            )

        # And the wire form of the splice is refused by the schema (N-13).
        good = adapters.attempt_from_session(
            session, card_id="c", arm_id="a", role=ArmRole.TREATMENT,
            facts=_delivered_facts(), requested=_stratum(), realized=_stratum(),
            attempt_id="attempt-s12-neg",
        ).to_dict()
        forged = dict(good, evidence_class="native-proven")
        self.assertEqual(forged["adapter_class"], "replay")
        with self.assertRaises(ContractError):
            io.load_schema("attempt").validate(forged)


class LedgerSpawnExitAccounting(_TempMixin):
    """REPAIR S-10. The event ledger is the framework's only EXTERNAL witness
    to how many attempts were started, so it is the only thing that can catch
    an attempt that was spawned and then never recorded."""

    negative_control = "evals/agentic/fixtures/native/tamper/deleted-entry.jsonl"

    def _ledger_with(self, pairs, *, name="spawn.jsonl"):
        ledger = self.caller_ledger(name)
        for attempt_id, exited in pairs:
            ledger.append(EventKind.SPAWN, attempt_id=attempt_id, session_id=None,
                          payload={"worker": attempt_id})
            if exited:
                ledger.append(EventKind.EXIT, attempt_id=attempt_id, session_id=None,
                              payload={"status": 0})
        return ledger

    def test_spawned_attempts_are_enumerable_and_reconcile_against_a_recorded_set(self):
        ledger = self._ledger_with([("a1", True), ("a2", True), ("a3", False)])
        reader = LedgerReader(ledger.path, key=None)

        acct = reader.spawn_exit_accounting()
        self.assertEqual(acct.spawned, ("a1", "a2", "a3"))
        self.assertEqual(acct.exited, ("a1", "a2"))
        self.assertEqual(acct.spawned_without_exit, ("a3",))
        self.assertEqual(acct.exited_without_spawn, ())
        self.assertEqual(acct.unattributed, 0)

        # The reconciliation the attempt ledger cannot do for itself: a1 and
        # a2 recorded, a3 spawned and then dropped before it reached the row
        # list -- exactly benchmark-spec §1.2's "retries collapsed into their
        # parent, hiding cost".
        self.assertEqual(acct.missing_from({"a1", "a2"}), ("a3",))
        self.assertEqual(acct.missing_from({"a1", "a2", "a3"}), ())

        # events_of_kind is the primitive underneath, and it is kind-typed.
        self.assertEqual(len(reader.events_of_kind(EventKind.SPAWN)), 3)
        self.assertEqual(len(reader.events_of_kind(EventKind.EXIT)), 2)
        with self.assertRaises(ContractError):
            reader.events_of_kind("spawn")  # type: ignore[arg-type]

    def test_spawned_attempts_are_enumerable_and_reconcile_against_a_recorded_set__negative(self):
        """The control: an UNATTRIBUTED spawn (no attempt_id) must be counted
        and surfaced, never quietly dropped -- a spawn nobody can attribute is
        missing evidence, not absent evidence. And a ledger whose SPAWN entries
        were deleted must not silently report a clean reconciliation: the chain
        walk names the deletion, which is what `tamper/deleted-entry.jsonl`
        (this class's `negative_control`) is the shipped artifact for."""
        ledger = self.caller_ledger("unattributed.jsonl")
        ledger.append(EventKind.SPAWN, attempt_id=None, session_id=None, payload={})
        ledger.append(EventKind.SPAWN, attempt_id="a1", session_id=None, payload={})
        ledger.append(EventKind.EXIT, attempt_id="ghost", session_id=None, payload={})
        acct = LedgerReader(ledger.path, key=None).spawn_exit_accounting()
        self.assertEqual(acct.unattributed, 1, "an unattributable spawn must be reported")
        self.assertEqual(acct.spawned, ("a1",))
        self.assertEqual(acct.exited_without_spawn, ("ghost",),
                         "an EXIT with no SPAWN is a hole, not a rounding error")
        # Reconciliation against a set that contains everything still leaves
        # the unattributed spawn visible, so "0 missing" can never be read as
        # "nothing unaccounted for".
        self.assertEqual(acct.missing_from({"a1", "ghost"}), ())
        self.assertGreater(acct.unattributed, 0)

        deleted = LedgerReader(NATIVE / "tamper" / "deleted-entry.jsonl", key=None)
        self.assertFalse(deleted.verify_chain().ok,
                         "a ledger with an entry removed must not verify")


class NativeClaimsRefuseAnEmptyHostWitness(_TempMixin):
    """REPAIR FOLLOWUP-2. `reporting.assert_native_claims` must not rest on
    one LedgerView implementation's internal policy.

    `event_ledger` is typed as the contract.LedgerView PROTOCOL, so any object
    with those methods satisfies it -- including a duck-typed reader whose
    `is_verified()` returns True for a ledger in which the host witnessed
    nothing. That is the shape review finding N-02 walked in through. The
    check now asks the chain directly.
    """

    negative_control = "evals/agentic/fixtures/native/ledgers/genuine-caller-asserted.jsonl"

    def _report_claiming_one_native(self):
        from evals.agentic.framework import reporting
        from evals.agentic.framework.accounting import Denominators

        return reporting.Report(
            manifest=None, denominators=Denominators(1, 1, 1, 0, 0, 0, 0),
            per_plugin={}, per_stratum_tokens={}, effects={}, noninferiority={},
            evidence={
                e: (1 if e is EvidenceClass.NATIVE_PROVEN else 0) for e in EvidenceClass
            },
            agreement=None, blocked=(), warnings=(),
        )

    def test_a_ledger_the_host_witnessed_nothing_in_cannot_back_a_native_claim(self):
        from evals.agentic.framework import reporting
        from evals.agentic.framework.contract import NativeProofRequired

        class _LyingReader:
            """Satisfies LedgerView and blesses itself. Nothing host-observed."""

            def has_event(self, event_id): return True
            def session_ids(self): return frozenset({"s"})
            def host_observed_session_ids(self): return frozenset({"s"})
            def is_verified(self): return True
            def signature_class(self, event_id): return SignatureClass.HOST_OBSERVED
            def verify_chain(self):
                return ChainVerification(
                    ok=True, first_bad_index=None, reason=None,
                    host_observed=0, caller_asserted=3, events=3,
                )

        with self.assertRaises(NativeProofRequired) as caught:
            reporting.assert_native_claims(self._report_claiming_one_native(), _LyingReader())
        self.assertIn("host_observed=0", str(caught.exception))

        # The real reader over a genuine caller-asserted ledger is refused too,
        # by the SAME fact rather than by luck: nothing here was host-observed.
        real = LedgerReader(NATIVE / "ledgers" / "genuine-caller-asserted.jsonl", key=None)
        self.assertEqual(real.verify_chain().host_observed, 0)
        with self.assertRaises(NativeProofRequired):
            reporting.assert_native_claims(self._report_claiming_one_native(), real)

    def test_a_ledger_the_host_witnessed_nothing_in_cannot_back_a_native_claim__negative(self):
        """The control: the new clause must not refuse everything (that would
        be a check that cannot distinguish), and it must not break a
        LedgerView double that predates it and has no `verify_chain` at all --
        `records()` is already documented as the OPTIONAL sixth capability and
        this one is probed the same way."""
        from evals.agentic.framework import reporting
        from evals.agentic.framework.contract import NativeProofRequired

        class _HostWitnessed:
            def has_event(self, event_id): return True
            def session_ids(self): return frozenset({"s"})
            def host_observed_session_ids(self): return frozenset({"s"})
            def is_verified(self): return True
            def signature_class(self, event_id): return SignatureClass.HOST_OBSERVED
            def verify_chain(self):
                return ChainVerification(
                    ok=True, first_bad_index=None, reason=None,
                    host_observed=4, caller_asserted=0, events=4,
                )

        # host_observed > 0: the clause passes it through (the other clauses
        # still apply -- this is belt and braces, not a replacement).
        reporting.assert_native_claims(self._report_claiming_one_native(), _HostWitnessed())

        class _NoVerifyChain(_HostWitnessed):
            verify_chain = None  # the pre-existing five-method double

        reporting.assert_native_claims(self._report_claiming_one_native(), _NoVerifyChain())

        # And a report with no native-proven attempt at all is still refused
        # on the first clause, so the new one did not become the only gate.
        from evals.agentic.framework.accounting import Denominators

        empty = reporting.Report(
            manifest=None, denominators=Denominators(0, 0, 0, 0, 0, 0, 0),
            per_plugin={}, per_stratum_tokens={}, effects={}, noninferiority={},
            evidence={e: 0 for e in EvidenceClass},
            agreement=None, blocked=(), warnings=(),
        )
        with self.assertRaises(NativeProofRequired) as caught:
            reporting.assert_native_claims(empty, _HostWitnessed())
        self.assertIn("NATIVE_PROVEN] == 0", str(caught.exception))


if __name__ == "__main__":
    unittest.main()



# ===========================================================================
# Replaying the REAL capture is still REPLAY evidence.
#
# This is the claim `fixtures/native/evidence/2026-09-07/PROVENANCE.md` makes,
# asserted rather than asserted-in-prose. It is the one thing a reader is most
# likely to get wrong once a genuine capture exists in the tree: a file
# recorded from a real CLI *looks* like native evidence, and reading it back
# must not be.
# ===========================================================================

class CaptureReplayStaysSimulated(_TempMixin):
    """A real capture, replayed, is SIMULATED. There is no path to promotion."""

    def test_replaying_the_real_capture_is_simulated_and_cannot_be_host_witnessed(self):
        capture = adapters.STREAMS_DIR() / "claude-2026-09-07.jsonl"
        self.assertTrue(capture.is_file(), "the committed capture is missing")
        grammar = load_grammar("claude-stream-json")

        ledger = self.caller_ledger("replayed-capture.jsonl")
        session = ReplaySession(str(capture), grammar, ledger, attempt_id="attempt-replay")
        turn = session.send("this text is not sent anywhere; the stream is a file")

        # The replay DOES parse the real stream -- that is what makes the point
        # sharp. It finds the real session id and the real turn ack...
        self.assertIsNotNone(session.session_id)
        self.assertTrue(turn.acked)
        self.assertIsNot(turn.usage.input_tokens, UNKNOWN)

        # ...and none of it is worth anything, because the host witnessed a
        # FILE, not a harness.
        reader = LedgerReader(ledger.path, key=None)
        chain = reader.verify_chain()
        self.assertTrue(chain.ok)
        self.assertEqual(chain.host_observed, 0)
        self.assertGreater(chain.caller_asserted, 0)
        self.assertEqual(reader.host_observed_session_ids(), frozenset())
        self.assertIs(session.adapter_class, AdapterClass.REPLAY)
        self.assertIs(
            evidence_class_for(session.adapter_class, chain), EvidenceClass.SIMULATED
        )

        # And the attempt built from it makes no native claim at all: the real
        # session id it just read is recorded in `notes`, never on the record.
        attempt = adapters.attempt_from_session(
            session, card_id="replayed-capture", arm_id="arm-replay",
            role=ArmRole.TREATMENT, facts=_delivered_facts(),
            requested=_stratum(), realized=_stratum(),
            attempt_id="attempt-replay",
        )
        self.assertIs(attempt.evidence_class, EvidenceClass.SIMULATED)
        self.assertIsNone(attempt.session_id)
        self.assertEqual(attempt.event_ids, ())
        self.assertFalse(attempt.claims_native)
        self.assertIn(session.session_id, attempt.notes)

    def test_a_host_observed_ledger_is_refused_for_the_capture_replay(self):
        """The only way a replay of the capture could be promoted is by handing
        it a host-observed ledger. `ReplaySession` refuses one outright."""
        capture = adapters.STREAMS_DIR() / "claude-2026-09-07.jsonl"
        with self.assertRaises(EvidencePromotionRefused):
            ReplaySession(str(capture), load_grammar("claude-stream-json"), self.host_ledger())

# ===========================================================================
# T26-T29 — the LIVE native forms.
#
# These four drive the REAL installed `claude` CLI through
# `CliDriver.spawn`, over a `HostLedger` the host itself minted
# (`witness=HOST_OBSERVED`). They are the only tests in this repository that
# can produce `NATIVE_PROVEN`, and they are unreachable unless a human passes
# an approval token on the command line:
#
#     python3 evals/agentic/run.py --id T26 --approval-token <tok>
#
# `run.py` sets `LIVE_APPROVAL_TOKEN` on this module and nothing else does.
# There is no environment-variable fallback, no default and no `--yes`
# (contract §10.6); under plain `unittest discover` the token is None and all
# four skip. The offline `*__offline_form` siblings above stay exactly as they
# were -- they remain what the catalog runs with no token, and they remain
# SIMULATED.
# ===========================================================================

#: Set ONLY by `run.py --id <TID> --approval-token <tok>`, in-process, on this
#: module object. Deliberately not read from `os.environ`: the token is a human
#: decision that must appear on the command line of the run it authorises.
LIVE_APPROVAL_TOKEN: "str | None" = None

#: Filled by whichever live form ran, so `run.py` can PRINT the harness-reported
#: session id rather than asserting one existed. Keyed by catalog ID.
LIVE_NATIVE_RESULTS: "dict[str, dict[str, object]]" = {}

#: Where an approved run's ledger / manifest / attempt records are persisted.
LIVE_EVIDENCE_DIR = NATIVE / "evidence" / "2026-09-07"


class _LiveNative(_TempMixin):
    """Shared plumbing for the four live forms. Drives nothing on its own."""

    #: The CLI whose stream grammar was captured (2026-09-07). `codex` has no
    #: capture, so `load_grammar` still raises for it and `spawn` refuses.
    driver_name = "claude"

    def require_live(self) -> str:
        token = LIVE_APPROVAL_TOKEN
        if not isinstance(token, str) or not token:
            self.skipTest(
                "native-required: no approval token on this run. This form drives the real "
                "installed claude CLI and is reachable only through "
                "`run.py --id <TID> --approval-token <tok>`; there is no environment "
                "fallback and no default (contract §10.6)."
            )
        return token

    def live_root(self):
        """A FRESH mkdtemp per card (§10.3). Nothing is ever reused."""
        root = pathlib.Path(tempfile.mkdtemp(prefix="agentic-live-native-"))
        self.addCleanup(shutil.rmtree, root, True)
        paths = {}
        for name in ("ws", "home", "plugins", "runs"):
            paths[name] = root / name
            paths[name].mkdir(parents=True)
        paths["root"] = root
        paths["mcp"] = root / "mcp.json"
        # §10.1's strict MCP config: an EMPTY server set, so --strict-mcp-config
        # means "no MCP servers at all" rather than "whichever ones this host
        # happens to have configured".
        paths["mcp"].write_text(json.dumps({"mcpServers": {}}), encoding="utf-8")
        return paths

    def live_manifest(self, token: str, run_id: str) -> Manifest:
        return Manifest(
            run_id=run_id, created_at=adapters.now_rfc3339(), git_commit="0" * 40,
            branch="feat/agentic-test-framework", offline=False,
            toolchain={"python": "3.12", "claude": self.cli_version()},
            lanes=("adapter",), estimands=(), noninferiority_margin=0.05,
            min_valid=5, min_clusters=8, planned_n={}, holdout_seed=1,
            catalog_digest="0" * 64, skipped=(), approvals=(token,),
        )

    def cli_version(self) -> str:
        config = load_driver_config(self.driver_name)
        proc = subprocess.run(
            [config.binary, "--version"], capture_output=True, text=True, timeout=60,
            stdin=subprocess.DEVNULL,
            env={"PATH": "/usr/bin:/bin", "HOME": str(self.tmp), "LANG": "en_US.UTF-8"},
        )
        return (proc.stdout or "").strip() or "unknown"

    def live_ledger(self, paths, run_id: str, name: str = "events.jsonl") -> HostLedger:
        ledger = HostLedger(
            paths["runs"] / name, run_id=run_id,
            witness=SignatureClass.HOST_OBSERVED,
        )
        self.addCleanup(ledger.close)
        return ledger

    def live_slots(self, paths, session_id: str) -> dict:
        """The §10.1 slot set for one live session.

        `model` and `effort` are None on purpose: `build_argv` drops a None slot
        AND the flag in front of it, so the session runs on the account's own
        default model at the CLI's default effort. Naming a model here would be
        this test choosing a stratum; letting the CLI choose it means the
        stratum is OBSERVED, which is what `realized` has to be.
        """
        return dict(
            model=None, effort=None, session_id=session_id,
            permission_mode="plan", allowed_tools="",
            workspace=str(paths["ws"]),
            system_append="Answer with a single short line and no preamble.",
            mcp_config=str(paths["mcp"]),
            home=str(paths["home"]), plugin_root=str(paths["plugins"]),
            config_dir=str(pathlib.Path.home() / ".claude"),
        )

    def live_driver(self, manifest: Manifest) -> CliDriver:
        return CliDriver(load_driver_config(self.driver_name), manifest=manifest)

    def assert_acked_on_the_stream(self, session, caller_minted: str) -> str:
        """The id came off a record on the HARNESS's own stream (§10.2).

        OBSERVED 2026-09-07, and it matters: `claude --session-id <uuid>` echoes
        that uuid back on its `system/init` record, so the acked id EQUALS the
        one the caller minted. §10.2 item 2 anticipates exactly this and settles
        it -- "if the harness echoes it back on the stream, that echo is the
        ack; if nothing is echoed, there is no ack". So the check that carries
        weight is not "the id is different" (it is not), it is "a record the
        host read off the child's stdout carried it". The offline negative
        control (`replay/no-session-ack.jsonl`) and T27's fork -- whose id the
        caller never chose -- are the two directions that make that distinction
        observable rather than asserted.
        """
        self.assertIsNotNone(
            session.session_id,
            "the harness announced no session id; §10.2 forbids promoting the "
            "caller-minted uuid into an ack",
        )
        self.assertIn(session.session_id, session.acked_session_ids)
        grammar = load_grammar(load_driver_config(self.driver_name).grammar)
        carried = [
            record for record in session.stream_records
            if grammar.session_ack.matches(record)
            and grammar.session_ack.extracted(record).get(grammar.session_id_field)
            == session.session_id
        ]
        self.assertTrue(
            carried,
            "no record on the harness's own stream carried this id, so it is a variable "
            "this test set rather than an acknowledgment (§10.2)",
        )
        del caller_minted
        return session.session_id

    def publish(self, tid: str, *, ledger: HostLedger, manifest: Manifest,
                summary: dict, attempt=None) -> None:
        """Persist the run's evidence and hand `run.py` something to print."""
        LIVE_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        stem = tid.lower()
        (LIVE_EVIDENCE_DIR / f"{stem}-ledger.jsonl").write_text(
            ledger.path.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (LIVE_EVIDENCE_DIR / f"{stem}-run-manifest.json").write_text(
            json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        if attempt is not None:
            (LIVE_EVIDENCE_DIR / f"{stem}-attempt.json").write_text(
                json.dumps(attempt.to_dict(), indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        (LIVE_EVIDENCE_DIR / "cli-version.txt").write_text(
            f"{load_driver_config(self.driver_name).binary}\n{self.cli_version()}\n",
            encoding="utf-8",
        )
        summary = dict(summary)
        summary.setdefault("evidence_dir", str(LIVE_EVIDENCE_DIR))
        LIVE_NATIVE_RESULTS[tid] = summary


class SessionTurnAcksLive(_LiveNative):
    """T26 LIVE. Two real turns against the installed claude CLI."""

    def test_session_and_turn_acks_bind_to_harness_reported_ids__live_native(self):
        token = self.require_live()
        paths = self.live_root()
        run_id = "run-live-T26-2026-09-07"
        manifest = self.live_manifest(token, run_id)
        ledger = self.live_ledger(paths, run_id)
        caller_minted = str(uuid.uuid4())
        session = self.live_driver(manifest).spawn(
            approval_token=token, mode="fresh", ledger=ledger, run_id=run_id,
            attempt_id="attempt-live-T26", **self.live_slots(paths, caller_minted),
        )
        self.addCleanup(session.close)

        first = session.send("Reply with exactly the word OK and nothing else.")
        sid = self.assert_acked_on_the_stream(session, caller_minted)
        self.assertEqual(
            sid, caller_minted,
            "OBSERVED 2026-09-07: this CLI echoes --session-id back on its init record, "
            "which §10.2 item 2 says IS the ack. Pinned as an assertion so a release that "
            "stops echoing reds this test instead of silently changing what "
            "host_observed_session_ids() contains.",
        )
        second = session.send("Reply with exactly the word AGAIN and nothing else.")

        self.assertTrue(first.acked, "turn 0 was never acknowledged on the harness stream")
        self.assertTrue(second.acked, "turn 1 was never acknowledged on the harness stream")
        self.assertEqual((first.index, second.index), (0, 1))
        self.assertEqual(session.turns, 2)
        self.assertEqual(
            session.invocations, 2,
            "claude --print is one-shot: turn 1 must be a second real invocation",
        )
        self.assertIsNotNone(first.ack_event_id)
        self.assertNotEqual(first.ack_event_id, second.ack_event_id)

        reader = ledger.verifier()
        acks = [e for e in reader.events() if e.kind is EventKind.TURN_ACK]
        self.assertEqual(len(acks), 2, "one ledger TURN_ACK per stream ack, not per write")
        self.assertEqual({e.session_id for e in acks}, {sid})
        for event in acks:
            self.assertIs(
                reader.signature_class(event.event_id), SignatureClass.HOST_OBSERVED,
                "the host read this ack off the child's stdout; it is not the subject's word",
            )
        self.assertIn(sid, reader.host_observed_session_ids())
        opens = [e for e in reader.events() if e.kind is EventKind.SESSION_OPEN]
        self.assertEqual(len(opens), 1)
        self.assertIsNone(
            opens[0].session_id,
            "SESSION_OPEN is written BEFORE any ack, so it can carry no session id (§10.2)",
        )
        self.assertEqual(opens[0].payload["caller_minted_session_id"], caller_minted)

        chain = reader.verify_chain()
        self.assertTrue(chain.ok, chain.reason)
        self.assertEqual(chain.caller_asserted, 0)
        self.assertGreater(chain.host_observed, 0)
        self.assertEqual(
            evidence_class_for(session.adapter_class, chain), EvidenceClass.NATIVE_PROVEN
        )
        self.publish("T26", ledger=ledger, manifest=manifest, summary={
            "session_id": sid, "caller_minted_session_id": caller_minted,
            "turns": session.turns, "invocations": session.invocations,
            "turn_acks": len(acks), "evidence_class": "native-proven",
            "cli": self.cli_version(),
            "usage": second.usage.to_dict(),
        })


class ResumeAndIsolationLive(_LiveNative):
    """T27 LIVE. Resume, fork, and two fresh sessions in ONE workspace."""

    CODEWORD = "ZEPHYR-NINE"

    def test_resume_continues_the_same_session_and_fork_records_its_parent__live_native(self):
        token = self.require_live()
        paths = self.live_root()
        run_id = "run-live-T27-2026-09-07"
        manifest = self.live_manifest(token, run_id)
        driver = self.live_driver(manifest)
        ledger = self.live_ledger(paths, run_id)
        before = protocols.snapshot_tree(paths["ws"])

        minted_a = str(uuid.uuid4())
        first = driver.spawn(
            approval_token=token, mode="fresh", ledger=ledger, run_id=run_id,
            attempt_id="attempt-live-T27-a", **self.live_slots(paths, minted_a),
        )
        self.addCleanup(first.close)
        first.send(
            f"Remember this codeword for later in our conversation: {self.CODEWORD}. "
            "Reply with exactly the word STORED."
        )
        sid_a = self.assert_acked_on_the_stream(first, minted_a)

        # -- resume: SAME session id, turns continue monotonically (§10.3) ----
        resumed = first.send(
            "What codeword did I ask you to remember? Reply with the codeword only."
        )
        self.assertEqual(
            first.session_id, sid_a,
            "§10.3: a resume that reports a DIFFERENT harness session id is a failure, "
            "not a rename",
        )
        self.assertEqual(set(first.acked_session_ids), {sid_a})
        self.assertEqual(first.turns, 2, "turns must continue from the prior high-water mark")
        self.assertIn(
            self.CODEWORD.split("-")[0].lower(), resumed.text.lower(),
            "the resumed session did not carry the earlier turn's context, so it is not "
            "the same conversation",
        )

        # -- fork: a NEW id whose SESSION_OPEN names its parent (§10.3) --------
        forked = driver.spawn(
            approval_token=token, mode="fork", ledger=ledger, run_id=run_id,
            attempt_id="attempt-live-T27-fork", parent_session_id=sid_a,
            **self.live_slots(paths, sid_a),
        )
        self.addCleanup(forked.close)
        fork_turn = forked.send(
            "What codeword did I ask you to remember? Reply with the codeword only."
        )
        sid_fork = forked.session_id
        self.assertIsNotNone(sid_fork)
        self.assertNotEqual(sid_fork, sid_a, "a fork must mint a new session id")
        self.assertNotIn(
            sid_fork, (minted_a, sid_a),
            "the fork's id is one the caller never chose -- the one place in this suite "
            "where a harness-minted id is observable independently of the --session-id echo",
        )
        self.assertIn(
            self.CODEWORD.split("-")[0].lower(), fork_turn.text.lower(),
            "a fork inherits the parent's context; this one did not",
        )
        opens = [
            e for e in ledger.verifier().events()
            if e.kind is EventKind.SESSION_OPEN and e.payload.get("mode") == "fork"
        ]
        self.assertEqual(len(opens), 1)
        self.assertEqual(opens[0].payload["parent_session_id"], sid_a)

        # -- a second FRESH session in the SAME workspace (§10.3, all three) ---
        minted_b = str(uuid.uuid4())
        fresh = driver.spawn(
            approval_token=token, mode="fresh", ledger=ledger, run_id=run_id,
            attempt_id="attempt-live-T27-b", **self.live_slots(paths, minted_b),
        )
        self.addCleanup(fresh.close)
        probe = fresh.send(
            "What codeword did I ask you to remember earlier in this conversation? "
            "If you have no earlier conversation with me, reply with exactly the word "
            "UNKNOWN and nothing else."
        )
        sid_b = self.assert_acked_on_the_stream(fresh, minted_b)
        self.assertNotEqual(sid_b, sid_a)
        after = protocols.snapshot_tree(paths["ws"])

        lowered = probe.text.lower()
        leaked = self.CODEWORD.split("-")[0].lower() in lowered
        disclaimed = any(
            marker in lowered for marker in (
                "unknown", "no earlier", "no prior", "not aware", "no codeword",
                "don't have", "do not have", "haven't", "have not",
            )
        )
        self.assertFalse(
            leaked,
            f"the fresh session knew the prior session's codeword: {probe.text!r} -- this "
            "is context carry-over, which is the failure §10.3 exists to detect",
        )
        self.assertTrue(
            disclaimed,
            f"the probe was neither answered as unknown nor disclaimed: {probe.text!r}",
        )
        answered_unknown = disclaimed and not leaked
        report = check_fresh_isolation(
            prior_session_id=sid_a, fresh_session_id=sid_b,
            before=before, after=after, probe_answered_as_unknown=answered_unknown,
        )
        self.assertEqual(
            protocols.diff_tree(before, after), (),
            "a live session must leave no artifact in the shared workspace",
        )
        self.assertTrue(
            report.isolated,
            f"fresh isolation failed: {report.why_not()}; probe answered {probe.text!r}",
        )

        reader = ledger.verifier()
        self.assertEqual(
            reader.host_observed_session_ids(), frozenset({sid_a, sid_fork, sid_b}),
            "exactly three harness-announced sessions, all host-observed",
        )
        chain = reader.verify_chain()
        self.assertTrue(chain.ok, chain.reason)
        self.assertEqual(chain.caller_asserted, 0)
        self.publish("T27", ledger=ledger, manifest=manifest, summary={
            "session_id": sid_a, "resumed_session_id": first.session_id,
            "fork_session_id": sid_fork, "fresh_session_id": sid_b,
            "turns_after_resume": first.turns,
            "workspace_diff": list(protocols.diff_tree(before, after)),
            "probe_answer": probe.text.strip()[:120],
            "evidence_class": "native-proven", "cli": self.cli_version(),
        })


class CancellationPathLive(_LiveNative):
    """T28 LIVE. A real mid-turn cancel of a real agent process GROUP."""

    def test_cancel_kills_the_process_group_and_tags_late_output__live_native(self):
        token = self.require_live()
        paths = self.live_root()
        run_id = "run-live-T28-2026-09-07"
        manifest = self.live_manifest(token, run_id)
        ledger = self.live_ledger(paths, run_id)
        minted = str(uuid.uuid4())
        session = self.live_driver(manifest).spawn(
            approval_token=token, mode="fresh", ledger=ledger, run_id=run_id,
            attempt_id="attempt-live-T28", **self.live_slots(paths, minted),
        )
        self.addCleanup(session.close)

        before_pids = protocols._live_descendant_pids(os.getpid())
        session.begin_turn(
            "Write a detailed 600-word history of the metric system, one paragraph per "
            "century, in plain prose."
        )
        pgid = session.pgid
        self.assertIsNotNone(pgid, "the child must be in its own process group")
        # Let the harness actually get going. The stream is deliberately NOT
        # drained here: whatever it emits in this window is output the host has
        # not consumed when the cancel is issued, which is exactly what §10.3
        # calls late output.
        deadline = time.monotonic() + 20.0
        while time.monotonic() < deadline and not live_group_members(pgid):
            time.sleep(0.05)
        self.assertTrue(live_group_members(pgid), "the harness process never appeared")
        time.sleep(4.0)
        self.assertTrue(session.pids(), "the turn must still be open when cancel lands")

        started = time.monotonic()
        session.cancel(grace_s=1.0)
        elapsed = time.monotonic() - started
        session.close()
        after_pids = protocols._live_descendant_pids(os.getpid())

        self.assertLess(
            elapsed, 10.0,
            "cancel must return promptly; a long pause means something else reaped the "
            "group and the group-signal property was never observed",
        )
        self.assertEqual(
            protocols.leaked_pids(before_pids, after_pids), frozenset(),
            "cancel must leave no orphan in the process tree",
        )
        self.assertEqual(session.pids(), frozenset(), "pids() after close() must be empty")
        self.assertEqual(live_group_members(pgid), frozenset(), "the process group survived")

        reader = ledger.verifier()
        events = list(reader.events())
        kinds = [e.kind for e in events]
        self.assertIn(EventKind.CANCEL_ISSUED, kinds)
        self.assertIn(EventKind.CANCEL_OBSERVED, kinds)
        self.assertLess(
            kinds.index(EventKind.CANCEL_ISSUED), kinds.index(EventKind.CANCEL_OBSERVED),
            "the issue is recorded BEFORE the signal, the observation after",
        )
        observed = events[kinds.index(EventKind.CANCEL_OBSERVED)]
        self.assertGreaterEqual(
            observed.payload["group_members_before"], 1,
            "the group had to be non-empty for a group cancel to mean anything",
        )
        self.assertEqual(
            observed.payload["group_survivors"], 0,
            "witnessed BEFORE the reap: a pid-only cancel leaves survivors here",
        )
        self.assertIn(EventKind.LATE_OUTPUT, kinds)
        late = [e for e in events if e.kind is EventKind.LATE_OUTPUT]
        self.assertGreater(late[0].payload["bytes"], 0)
        self.assertFalse(late[0].payload["credited"], "late output is recorded, not credited")
        self.assertTrue(session.arrived_after_terminal)
        for event in events:
            self.assertIs(
                reader.signature_class(event.event_id), SignatureClass.HOST_OBSERVED
            )
        chain = reader.verify_chain()
        self.assertTrue(chain.ok, chain.reason)
        self.assertEqual(chain.caller_asserted, 0)
        self.publish("T28", ledger=ledger, manifest=manifest, summary={
            "session_id": session.session_id,
            "cancel_seconds": round(elapsed, 3),
            "group_members_before": observed.payload["group_members_before"],
            "group_survivors": observed.payload["group_survivors"],
            "late_bytes": late[0].payload["bytes"],
            "arrived_after_terminal": session.arrived_after_terminal,
            "evidence_class": "native-proven", "cli": self.cli_version(),
        })


class EventLedgerIntegrityLive(_LiveNative):
    """T29 LIVE. A real host ledger, verified in-process, backing a real Attempt."""

    def test_chain_verifies_and_names_the_first_bad_index_per_tamper__live_native(self):
        token = self.require_live()
        paths = self.live_root()
        run_id = "run-live-T29-2026-09-07"
        attempt_id = "attempt-live-T29"
        manifest = self.live_manifest(token, run_id)
        ledger = self.live_ledger(paths, run_id)
        minted = str(uuid.uuid4())
        session = self.live_driver(manifest).spawn(
            approval_token=token, mode="fresh", ledger=ledger, run_id=run_id,
            attempt_id=attempt_id, **self.live_slots(paths, minted),
        )
        self.addCleanup(session.close)
        turn = session.send("Reply with exactly the word OK and nothing else.")
        sid = self.assert_acked_on_the_stream(session, minted)

        reader = ledger.verifier()
        chain = reader.verify_chain()
        self.assertTrue(chain.ok, chain.reason)
        self.assertIsNone(chain.first_bad_index)
        self.assertEqual(chain.caller_asserted, 0)
        self.assertGreater(chain.host_observed, 0)
        self.assertTrue(
            reader.is_verified(),
            f"the minting process must be able to bless its own ledger: "
            f"{reader.verification_reason()}",
        )
        self.assertNotIn(
            adapters._run_key_bytes(ledger.key).hex(),
            ledger.path.read_text(encoding="utf-8"),
            "the run key must never reach the ledger file",
        )

        realized = Stratum(
            provider="anthropic", model=turn.usage.model_id, revision="unknown",
            effort="default", harness=f"claude-code/{self.cli_version()}",
        )
        attempt = adapters.attempt_from_session(
            session, card_id="live-native-smoke", arm_id="arm-live-native",
            role=ArmRole.TREATMENT, facts=_delivered_facts(),
            requested=realized, realized=realized,
            run_id=run_id, attempt_id=attempt_id,
        )
        self.assertIs(attempt.evidence_class, EvidenceClass.NATIVE_PROVEN)
        self.assertIs(attempt.adapter_class, AdapterClass.NATIVE)
        self.assertEqual(attempt.session_id, sid)
        self.assertTrue(
            attempt.event_ids,
            "a NATIVE_PROVEN attempt must cite the host-observed events behind it",
        )
        self.assertTrue(attempt.claims_native)
        assert_native_backed(attempt, reader)   # raises ForgedProvenance if it does not

        # The same attempt is refused by a reader with no run key -- §5.3's
        # "cannot forge, and cannot bless" holds in this direction too.
        keyless = LedgerReader(ledger.path, key=None)
        self.assertFalse(keyless.is_verified())
        self.assertEqual(
            keyless.verification_reason(), LedgerReader.UNVERIFIABLE_IN_THIS_PROCESS
        )
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(attempt, keyless)

        # And an invented event id is refused against the REAL verified ledger.
        forged = dataclasses.replace(attempt, event_ids=(str(uuid.uuid4()),))
        with self.assertRaises(ForgedProvenance):
            assert_native_backed(forged, reader)

        self.publish("T29", ledger=ledger, manifest=manifest, attempt=attempt, summary={
            "session_id": sid, "attempt_id": attempt.attempt_id,
            "evidence_class": attempt.evidence_class.value,
            "event_ids": len(attempt.event_ids),
            "chain_events": chain.events, "host_observed": chain.host_observed,
            "caller_asserted": chain.caller_asserted,
            "is_verified": reader.is_verified(),
            "cli": self.cli_version(),
        })


#: The approval-gated LIVE form for each `native-required` catalog ID.
#:
#: The catalog entry itself is UNCHANGED and still names the `__offline_form`
#: method, so `run.py --catalog` with no token prints exactly the same four
#: `BLOCKED — approval required (native-required)` lines and exactly the same
#: frozen summary as before. This table is the *only* way the live form becomes
#: reachable, and `run.py` reaches it only when a human supplied
#: `--approval-token` on the command line (contract §10.6).
LIVE_FORMS: "dict[str, tuple[str, str]]" = {
    "T26": (
        "SessionTurnAcksLive",
        "test_session_and_turn_acks_bind_to_harness_reported_ids__live_native",
    ),
    "T27": (
        "ResumeAndIsolationLive",
        "test_resume_continues_the_same_session_and_fork_records_its_parent__live_native",
    ),
    "T28": (
        "CancellationPathLive",
        "test_cancel_kills_the_process_group_and_tags_late_output__live_native",
    ),
    "T29": (
        "EventLedgerIntegrityLive",
        "test_chain_verifies_and_names_the_first_bad_index_per_tamper__live_native",
    ),
}
