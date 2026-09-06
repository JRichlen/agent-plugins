"""evals.agentic.tests.test_protocols — real hooks, real MCP, real subprocesses
(protocol lane, T19-T24, contract §3.8 / §8.3).

Every test in this module spawns a REAL subprocess: a real live hook handler
from ``plugins/*/hooks/**``, the real agent-compiler MCP server, or a real
fixture worker script. Nothing is mocked, stubbed, or replayed. Each test
class mixes in ``_PidLeakMixin`` so `leaked_pids(before, after) ==
frozenset()` is asserted after every single test, not just once for the
whole module (contract §8.3's acceptance line).

FINDING surfaced by this module (not a testing-framework defect — a real
defect in the shipped ``redgate`` plugin, out of this lane's ownership):
``plugins/redgate/hooks/hooks.json`` writes its two commands as
``${CLAUDE_PLUGIN_ROOT}/hooks-handlers/<script>.sh``. In every other plugin
that pattern resolves against the PLUGIN ROOT (see ``voice``, whose
``hooks-handlers/`` really does sit at the plugin root, and ``agent-compiler``,
whose commands say ``${CLAUDE_PLUGIN_ROOT}/hooks/<script>.py`` and whose
scripts really do live under ``hooks/``). redgate's own handler scripts,
however, live one level deeper, at
``plugins/redgate/hooks/hooks-handlers/<script>.sh`` — so the command
``hooks.json`` actually wires is a 404: running it literally, exactly as a
real Claude Code session would, exits 127 with "No such file or directory".
Neither of redgate's two hooks (the PreToolUse write-guard and the
SessionStart injection) can ever fire today. ``HookDiscoveryAndExec`` asserts
this literal, observed fact rather than silently rerouting the command to
where the file "should" be — discovery must stay honest even when what it
discovers is broken. ``RedgateWriteGuard`` and ``SessionStartInjection``
separately exercise the handler scripts at their real, existing path to prove
the underlying shell logic is otherwise correct, so the fix redgate needs is a
one-line path correction in its own ``hooks.json``, not a rewrite of either
handler.

A second, smaller deviation from the T19-T24 backlog text, also verified
empirically rather than assumed: redgate's ``session-start.sh`` does not
emit JSON at all (it echoes plain prose lines, or nothing) — only voice's
does. ``SessionStartInjection`` asserts each script's real, observed
contract rather than a shared JSON expectation.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile
import time
import unittest

from evals.agentic.framework.protocols import (
    HookSpec,
    McpStdioClient,
    WorkerPool,
    _live_descendant_pids,
    _scrubbed_env,
    diff_tree,
    discover_hooks,
    leaked_pids,
    run_hook,
    snapshot_tree,
)

_HERE = pathlib.Path(__file__).resolve()
REPO_ROOT = _HERE.parents[3]
FIXTURES = _HERE.parents[1] / "fixtures" / "protocols"
PAYLOADS = FIXTURES / "payloads"
WORKERS_DIR = FIXTURES / "workers"
MUTANTS = FIXTURES / "mutants"

AGENT_COMPILER_HOOKS_DIR = REPO_ROOT / "plugins" / "agent-compiler" / "hooks"
REDGATE_GUARD_SCRIPT = (
    REPO_ROOT / "plugins" / "redgate" / "hooks" / "hooks-handlers" / "guard-redgate-paths.sh"
)
REDGATE_SESSION_SCRIPT = (
    REPO_ROOT / "plugins" / "redgate" / "hooks" / "hooks-handlers" / "session-start.sh"
)
VOICE_SESSION_SCRIPT = REPO_ROOT / "plugins" / "voice" / "hooks-handlers" / "session-start.sh"
MCP_SERVER = REPO_ROOT / "plugins" / "agent-compiler" / "scripts" / "mcp_server.py"
AGENT_COMPILER_REGISTRY = REPO_ROOT / "plugins" / "agent-compiler" / "registry"


def _load_payload(name: str, cwd: pathlib.Path | None = None) -> dict:
    doc = json.loads((PAYLOADS / name).read_text())
    if cwd is not None:
        doc["cwd"] = str(cwd)
    return doc


def _pretooluse_payload(file_path, cwd: pathlib.Path | None = None) -> dict:
    doc = _load_payload("pretooluse-write-generic.json", cwd)
    doc["tool_input"]["file_path"] = str(file_path)
    return doc


class _PidLeakMixin:
    """Every subprocess test asserts leaked_pids(before, after) == frozenset()."""

    def setUp(self) -> None:
        super().setUp()
        self._pid_snapshot_before = _live_descendant_pids(os.getpid())

    def tearDown(self) -> None:
        after = _live_descendant_pids(os.getpid())
        leaked = leaked_pids(self._pid_snapshot_before, after)
        self.assertEqual(leaked, frozenset(), f"leaked pids after test: {leaked}")
        super().tearDown()


# ---------------------------------------------------------------------------
# T19 — hook discovery and real hook-subprocess execution contract
# ---------------------------------------------------------------------------

class HookDiscoveryAndExec(_PidLeakMixin, unittest.TestCase):

    def test_discovers_exactly_the_live_marketplace_hooks(self):
        specs = discover_hooks(REPO_ROOT)
        seen = {(s.plugin, s.event, s.matcher) for s in specs}
        expected = {
            ("agent-compiler", "UserPromptSubmit", ""),
            ("agent-compiler", "PreToolUse", "Write|Edit|MultiEdit"),
            ("redgate", "PreToolUse", "Write|Edit|MultiEdit|NotebookEdit"),
            ("redgate", "SessionStart", "startup|clear|compact"),
            ("voice", "SessionStart", "startup|clear|compact"),
        }
        self.assertEqual(seen, expected)
        self.assertEqual(len(specs), 5)
        for spec in specs:
            self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", spec.command,
                              "the variable must already be expanded")
            self.assertTrue(pathlib.Path(spec.source_file).is_file())

    def test_synthetic_plugin_tree_has_exactly_three_hooks(self):
        specs = discover_hooks(FIXTURES)
        self.assertEqual(len(specs), 3)
        self.assertEqual({s.plugin for s in specs}, {"plugin-alpha", "plugin-beta"})

    def test_negative_hardcoded_discovery_would_miss_a_fourth_hook(self):
        # A discovery function returning a fixed list of plugin names (or any
        # count baked in at write time) would report the SAME 3 hooks against
        # this mutated tree that it reports against the unmutated one above --
        # indistinguishable, and the whole point of T19 is that this must not
        # happen. The real parser must see the fourth hook.
        mutated_root = FIXTURES / "mutated-fourth-hook-root"
        specs = discover_hooks(mutated_root)
        self.assertEqual(len(specs), 4, "discovery missed the added fourth hook")
        self.assertEqual({s.plugin for s in specs},
                          {"plugin-alpha", "plugin-beta", "plugin-gamma"})

    def test_payload_fixtures_share_the_real_envelope_shape(self):
        # Documents the PreToolUse/PostToolUse/UserPromptSubmit/SessionStart
        # payload shapes Claude Code emits (deliverable requirement), even
        # though no live hook today listens on PostToolUse.
        names = (
            "pretooluse-write-generic.json", "posttooluse-write-generic.json",
            "usersubmitprompt-agent-intent.json", "usersubmitprompt-plain.json",
            "sessionstart-startup.json", "sessionstart-clear.json",
            "sessionstart-compact.json",
        )
        for name in names:
            with self.subTest(name=name):
                doc = _load_payload(name)
                for key in ("session_id", "transcript_path", "cwd", "hook_event_name"):
                    self.assertIn(key, doc)

    def test_every_live_handler_executes_and_records_exit_code(self):
        specs = discover_hooks(REPO_ROOT)
        self.assertEqual(len(specs), 5)
        results = []
        for spec in specs:
            with tempfile.TemporaryDirectory(prefix="agentic-hookrun-") as td:
                cwd = pathlib.Path(td)
                payload = self._payload_for(spec, cwd)
                result = run_hook(spec, payload, cwd=cwd, timeout_s=10.0)
            results.append(result)
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertIsInstance(r.exit_code, int)
            self.assertIsInstance(r.duration_ms, int)

        # See the module docstring FINDING: redgate's two hooks are wired to
        # a path that does not exist. Assert the real, observed fact.
        redgate_results = [r for r in results if r.spec.plugin == "redgate"]
        self.assertEqual(len(redgate_results), 2)
        for r in redgate_results:
            self.assertEqual(
                r.exit_code, 127,
                "redgate's hooks.json command no longer 404s -- if this was "
                "fixed upstream, update this test and the module docstring",
            )
            self.assertIn("No such file or directory", r.stderr)

        # agent-compiler and voice ARE correctly wired.
        for r in results:
            if r.spec.plugin != "redgate":
                self.assertNotEqual(r.exit_code, 127,
                                     f"{r.spec.plugin}/{r.spec.event} unexpectedly 404s")

    @staticmethod
    def _payload_for(spec: HookSpec, cwd: pathlib.Path) -> dict:
        if spec.event == "UserPromptSubmit":
            return _load_payload("usersubmitprompt-plain.json", cwd)
        if spec.event == "SessionStart":
            return _load_payload("sessionstart-startup.json", cwd)
        if spec.event == "PreToolUse":
            target = cwd / "harmless.md"
            target.write_text("harmless fixture content\n")
            return _pretooluse_payload(target, cwd)
        raise AssertionError(f"no fixture payload wired for event {spec.event!r}")


# ---------------------------------------------------------------------------
# T20 — agent-compiler hooks: prompt injection and imageHash write denial
# ---------------------------------------------------------------------------

class AgentCompilerHooks(_PidLeakMixin, unittest.TestCase):

    @staticmethod
    def _run(script: str, payload: dict, cwd: pathlib.Path):
        command = f"python3 {AGENT_COMPILER_HOOKS_DIR / script}"
        spec = HookSpec(plugin="agent-compiler", event="test-harness", matcher="",
                         command=command, source_file=str(AGENT_COMPILER_HOOKS_DIR / "hooks.json"))
        return run_hook(spec, payload, cwd=cwd, timeout_s=10.0)

    def test_four_real_subprocess_outcomes_inject_silent_deny_allow(self):
        with tempfile.TemporaryDirectory() as td:
            cwd = pathlib.Path(td)

            r_inject = self._run("suggest-compiler.py",
                                  _load_payload("usersubmitprompt-agent-intent.json", cwd), cwd)
            r_silent = self._run("suggest-compiler.py",
                                  _load_payload("usersubmitprompt-plain.json", cwd), cwd)

            compiled = cwd / "compiled-agent.md"
            compiled.write_text("compiled by agent-compiler; imageHash: deadbeef\nbody\n")
            r_deny = self._run("guard-compiled-agents.py", _pretooluse_payload(compiled, cwd), cwd)

            ordinary = cwd / "ordinary.md"
            ordinary.write_text("just an ordinary file\n")
            r_allow = self._run("guard-compiled-agents.py", _pretooluse_payload(ordinary, cwd), cwd)

        self.assertEqual(r_inject.exit_code, 0)
        self.assertIsNotNone(r_inject.json, f"stdout: {r_inject.stdout!r}")
        self.assertIn("additionalContext", r_inject.json)
        self.assertIn("agent-compiler", r_inject.json["additionalContext"])

        self.assertEqual(r_silent.exit_code, 0)
        self.assertEqual(r_silent.stdout.strip(), "")
        self.assertIsNone(r_silent.json)

        self.assertEqual(r_deny.exit_code, 0)  # decision is IN the JSON, not the exit code
        self.assertIsNotNone(r_deny.json)
        self.assertEqual(
            r_deny.json["hookSpecificOutput"]["permissionDecision"], "deny",
            "this is the field Claude Code actually reads as a denial",
        )

        self.assertEqual(r_allow.exit_code, 0)
        self.assertIsNone(r_allow.json, "an allowed write must be silent")

    def test_negative_deny_everything_mutant_would_wrongly_deny_the_allow_case(self):
        # Named negative control: "A guard that denies EVERY write ... would
        # break the harness while passing a deny-only test." This mutant IS
        # that failing guard; running it against the exact allow-case payload
        # from the test above proves that test is not vacuous.
        with tempfile.TemporaryDirectory() as td:
            cwd = pathlib.Path(td)
            ordinary = cwd / "ordinary.md"
            ordinary.write_text("just an ordinary file\n")
            spec = HookSpec(plugin="agent-compiler", event="test-harness", matcher="",
                             command=f"python3 {MUTANTS / 'guard-deny-everything.py'}",
                             source_file=str(MUTANTS / "guard-deny-everything.py"))
            result = run_hook(spec, _pretooluse_payload(ordinary, cwd), cwd=cwd, timeout_s=10.0)
        self.assertIsNotNone(result.json)
        self.assertEqual(result.json["hookSpecificOutput"]["permissionDecision"], "deny",
                          "the mutant should wrongly deny an ordinary write")


# ---------------------------------------------------------------------------
# T21 — redgate PreToolUse denies writes to a ratified contract mid-round
# ---------------------------------------------------------------------------

class RedgateWriteGuard(_PidLeakMixin, unittest.TestCase):

    @staticmethod
    def _scaffold_run(root: pathlib.Path, slug: str, phase: str) -> pathlib.Path:
        run_dir = root / ".redgate" / slug
        run_dir.mkdir(parents=True)
        (run_dir / "manifest").write_text(f"slug={slug}\nphase={phase}\nround=1\nround_budget=4\n")
        (run_dir / "CRITERIA.md").write_text("template criteria\n")
        (run_dir / "check.sh").write_text("#!/bin/sh\nexit 1\n")
        return run_dir

    @staticmethod
    def _run_guard(script: pathlib.Path, cwd: pathlib.Path, file_path) -> "HookResult":
        spec = HookSpec(plugin="redgate", event="PreToolUse",
                         matcher="Write|Edit|MultiEdit|NotebookEdit",
                         command=f"bash {script}", source_file=str(script))
        payload = {"session_id": "s", "transcript_path": "/tmp/t", "cwd": str(cwd),
                   "hook_event_name": "PreToolUse", "tool_name": "Write",
                   "tool_input": {"file_path": str(file_path)}}
        return run_hook(spec, payload, cwd=cwd, timeout_s=10.0)

    def test_denies_ratified_contract_write_in_trace_phase(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            run_dir = self._scaffold_run(root, "fx-run", "TRACE")
            result = self._run_guard(REDGATE_GUARD_SCRIPT, root, run_dir / "CRITERIA.md")
        self.assertEqual(result.exit_code, 2)
        self.assertIn("DENY", result.stderr)

    def test_allows_arm_phase_write_before_ratification(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            run_dir = self._scaffold_run(root, "fx-run", "ARM")
            result = self._run_guard(REDGATE_GUARD_SCRIPT, root, run_dir / "CRITERIA.md")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stderr, "")

    def test_allows_unrelated_path_regardless_of_phase(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            self._scaffold_run(root, "fx-run", "TRACE")
            unrelated = root / "README.md"
            unrelated.write_text("hi\n")
            result = self._run_guard(REDGATE_GUARD_SCRIPT, root, unrelated)
        self.assertEqual(result.exit_code, 0)

    def test_legacy_middle_phase_also_denies(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            run_dir = self._scaffold_run(root, "fx-run", "MIDDLE")
            result = self._run_guard(REDGATE_GUARD_SCRIPT, root, run_dir / "check.sh")
        self.assertEqual(result.exit_code, 2)

    def test_negative_path_only_mutant_would_wrongly_deny_the_arm_case(self):
        # Named negative control: "A handler that denies on path match alone,
        # ignoring phase and ratification -- it would block legitimate ARM
        # authoring." Prove the real handler's ARM-phase allow (above) is not
        # vacuous by showing this mutant gets it wrong.
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            run_dir = self._scaffold_run(root, "fx-run", "ARM")
            mutant = MUTANTS / "guard-redgate-path-only.sh"
            result = self._run_guard(mutant, root, run_dir / "CRITERIA.md")
        self.assertEqual(result.exit_code, 2,
                          "path-only mutant should wrongly deny a legitimate ARM-phase write")


# ---------------------------------------------------------------------------
# T22 — SessionStart injection: redgate and voice
# ---------------------------------------------------------------------------

class SessionStartInjection(_PidLeakMixin, unittest.TestCase):
    MATCHERS = ("startup", "clear", "compact")

    @staticmethod
    def _run(script: pathlib.Path, cwd: pathlib.Path, source: str):
        spec = HookSpec(plugin="test-harness", event="SessionStart", matcher=source,
                         command=f"bash {script}", source_file=str(script))
        payload = {"session_id": "s", "transcript_path": "/tmp/t", "cwd": str(cwd),
                   "hook_event_name": "SessionStart", "source": source}
        return run_hook(spec, payload, cwd=cwd, timeout_s=10.0)

    def test_voice_emits_one_bounded_json_object_on_every_matcher(self):
        for source in self.MATCHERS:
            with self.subTest(source=source):
                with tempfile.TemporaryDirectory() as td:
                    result = self._run(VOICE_SESSION_SCRIPT, pathlib.Path(td), source)
                self.assertEqual(result.exit_code, 0)
                self.assertIsNotNone(
                    result.json, f"voice stdout did not parse as one JSON object: {result.stdout!r}")
                ctx = result.json["hookSpecificOutput"]["additionalContext"]
                self.assertTrue(
                    0 < len(ctx) < 4000,
                    "voice's own contract: 'a pointer to the skills, not a copy of them'")

    def test_redgate_names_an_unfinished_run_as_plain_text_not_json(self):
        # DEVIATION from the literal T22 backlog text -- see module docstring.
        for source in self.MATCHERS:
            with self.subTest(source=source):
                with tempfile.TemporaryDirectory() as td:
                    root = pathlib.Path(td)
                    run_dir = root / ".redgate" / "fx-run"
                    run_dir.mkdir(parents=True)
                    (run_dir / "manifest").write_text("slug=fx-run\nphase=TRACE\nround=2\n")
                    result = self._run(REDGATE_SESSION_SCRIPT, root, source)
                self.assertEqual(result.exit_code, 0)
                self.assertIsNone(result.json, "redgate's session-start.sh does not emit JSON")
                self.assertIn("fx-run", result.stdout)
                self.assertIn("TRACE", result.stdout)

    def test_redgate_empty_but_valid_when_no_run_exists(self):
        with tempfile.TemporaryDirectory() as td:
            result = self._run(REDGATE_SESSION_SCRIPT, pathlib.Path(td), "startup")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(result.stdout, "")

    def test_negative_two_json_objects_would_break_the_single_object_contract(self):
        with tempfile.TemporaryDirectory() as td:
            result = self._run(MUTANTS / "session-start-double-print.sh", pathlib.Path(td), "startup")
        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.json, "two concatenated JSON objects must not parse as ONE")

    def test_negative_unbounded_injection_fails_the_bound_check(self):
        with tempfile.TemporaryDirectory() as td:
            result = self._run(MUTANTS / "session-start-unbounded.sh", pathlib.Path(td), "startup")
        self.assertIsNotNone(result.json)
        ctx = result.json["hookSpecificOutput"]["additionalContext"]
        self.assertFalse(0 < len(ctx) < 4000,
                          "this mutant's huge payload should fail the bound assertion used above")


# ---------------------------------------------------------------------------
# T23 — MCP read-only inspect probe against the agent-compiler kernel
# ---------------------------------------------------------------------------

class McpInspectReadOnly(_PidLeakMixin, unittest.TestCase):

    def test_handshake_tools_list_and_read_only_inspect(self):
        before_registry = snapshot_tree(AGENT_COMPILER_REGISTRY, exclude=("__pycache__",))
        with tempfile.TemporaryDirectory(prefix="agentic-mcp-") as td:
            cwd = pathlib.Path(td)
            before_cwd = snapshot_tree(cwd)
            env = _scrubbed_env(cwd / ".home")
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            with McpStdioClient([sys.executable, str(MCP_SERVER)], cwd=cwd,
                                 env=env, timeout_s=15.0) as client:
                init = client.initialize()
                self.assertEqual(init["serverInfo"]["name"], "agent-compiler")
                tools = {t["name"] for t in client.tools_list()}
                self.assertEqual(tools, {"inspect", "compile", "explain", "render"})

                result = client.call_tool("inspect", {})
                self.assertFalse(result.get("isError", False), result)
                payload = json.loads(result["content"][0]["text"])
                self.assertIn("modules", payload)
                self.assertIsInstance(payload["modules"], list)
                self.assertGreater(len(payload["modules"]), 0)

                self.assertIsNotNone(client.pid)
            after_cwd = snapshot_tree(cwd)
        after_registry = snapshot_tree(AGENT_COMPILER_REGISTRY, exclude=("__pycache__",))

        self.assertEqual(diff_tree(before_cwd, after_cwd), (),
                          "the probe's own scratch cwd must be untouched")
        self.assertEqual(diff_tree(before_registry, after_registry), (),
                          "inspect must make zero writes to the registry it reads")

    def test_negative_metadata_only_check_does_not_prove_the_server_starts(self):
        plugin_json = json.loads(
            (REPO_ROOT / "plugins" / "agent-compiler" / ".claude-plugin" / "plugin.json").read_text())
        # This is the vacuous check named in T23's negative control: it would
        # "pass" even for a server that crashes on launch.
        self.assertIn("kernel", plugin_json.get("mcpServers", {}))

        # The REAL probe catches exactly that case, which the metadata check cannot:
        with tempfile.TemporaryDirectory() as td:
            cwd = pathlib.Path(td)
            with self.assertRaises(Exception):
                with McpStdioClient([sys.executable, str(MUTANTS / "broken_mcp_server.py")],
                                     cwd=cwd, timeout_s=5.0) as client:
                    client.initialize()

    def test_negative_a_write_during_inspect_is_caught_by_diff_tree(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            before = snapshot_tree(root)
            (root / "sneaky.txt").write_text("a write that a read-only probe must never make")
            after = snapshot_tree(root)
        self.assertEqual(diff_tree(before, after), ("sneaky.txt",))


# ---------------------------------------------------------------------------
# T24 — subprocess worker coordination, fault, and late result
# ---------------------------------------------------------------------------

class SubprocessLifecycle(_PidLeakMixin, unittest.TestCase):

    def test_coordination_order_independent_of_completion_order(self):
        with tempfile.TemporaryDirectory() as td:
            pool = WorkerPool(cwd=pathlib.Path(td), timeout_s=10.0)
            try:
                pool.spawn("slow", [sys.executable, str(WORKERS_DIR / "worker_sleep.py"), "0.4", "slow"])
                pool.spawn("fast", [sys.executable, str(WORKERS_DIR / "worker_sleep.py"), "0.05", "fast"])
                results = pool.collect()
            finally:
                pool.close()
        self.assertEqual([r.worker_id for r in results], ["slow", "fast"],
                          "collection order must be spawn order, not completion order")
        for r in results:
            self.assertEqual(r.exit_code, 0)
            self.assertFalse(r.arrived_after_terminal)
            payload = json.loads(r.stdout)
            self.assertEqual(payload["label"], r.worker_id)

    def test_fault_worker_exits_nonzero_and_is_distinguished_from_incomplete(self):
        with tempfile.TemporaryDirectory() as td:
            pool = WorkerPool(cwd=pathlib.Path(td), timeout_s=10.0)
            try:
                pool.spawn("bad", [sys.executable, str(WORKERS_DIR / "worker_fault.py"), "7"])
                results = pool.collect()
            finally:
                pool.close()
        self.assertEqual(results[0].exit_code, 7)
        self.assertIsNone(results[0].signalled)
        self.assertFalse(results[0].arrived_after_terminal)
        self.assertIn("simulating a crash", results[0].stderr)

    def test_signalled_worker_is_distinguished_from_a_clean_fault(self):
        with tempfile.TemporaryDirectory() as td:
            pool = WorkerPool(cwd=pathlib.Path(td), timeout_s=10.0)
            try:
                pool.spawn("killme", [sys.executable, str(WORKERS_DIR / "worker_sleep.py"), "30", "killme"])
                time.sleep(0.2)
                pool.cancel("killme")
                results = pool.collect()
            finally:
                pool.close()
        r = results[0]
        self.assertEqual(r.signalled, "SIGTERM")
        self.assertIsNone(r.exit_code)
        self.assertTrue(r.arrived_after_terminal)

    def test_late_result_after_cancel_is_recorded_but_flagged_not_delivered(self):
        with tempfile.TemporaryDirectory() as td:
            pool = WorkerPool(cwd=pathlib.Path(td), timeout_s=10.0)
            try:
                pool.spawn("late", [sys.executable, str(WORKERS_DIR / "worker_ignore_sigterm.py"), "1.0"])
                time.sleep(0.2)
                pool.cancel("late")  # SIGTERM; the worker ignores it and keeps going
                results = pool.collect()  # must still capture the eventual real exit
            finally:
                pool.close()
        r = results[0]
        self.assertTrue(
            r.arrived_after_terminal,
            "a result that finishes after cancellation must be flagged, never silently "
            "accepted as an ordinary delivery",
        )
        self.assertEqual(r.exit_code, 0)  # it DID finish -- but arrived_after_terminal is set
        payload = json.loads(r.stdout)
        self.assertEqual(payload["label"], "late-finished-after-cancel")
        self.assertGreaterEqual(payload["sigterms_ignored"], 1)

    def test_negative_discarding_post_cancel_output_would_hide_continued_work(self):
        # Named negative control: "A harness that discards post-cancel output
        # ... hides the fact that the agent kept working after a stop." Prove
        # WorkerPool does not discard it: the late worker's real stdout must
        # be present and parseable, which a discarding implementation would
        # report as empty.
        with tempfile.TemporaryDirectory() as td:
            pool = WorkerPool(cwd=pathlib.Path(td), timeout_s=10.0)
            try:
                pool.spawn("late2", [sys.executable, str(WORKERS_DIR / "worker_ignore_sigterm.py"), "0.6"])
                time.sleep(0.2)  # let the worker install its SIGTERM trap first
                pool.cancel("late2")
                r = pool.collect()[0]
            finally:
                pool.close()
        self.assertNotEqual(r.stdout.strip(), "", "post-cancel output must not be discarded")
        self.assertTrue(r.arrived_after_terminal)

    def test_leaked_pids_is_nonempty_mid_run_and_empty_after_close(self):
        # Proves leaked_pids()/live-descendant accounting is not vacuously
        # empty: workers really are running mid-test (nonempty), and really
        # are gone after close() (empty) -- the negative half of T24's own
        # cleanup assertion.
        before = _live_descendant_pids(os.getpid())
        with tempfile.TemporaryDirectory() as td:
            pool = WorkerPool(cwd=pathlib.Path(td), timeout_s=10.0)
            pool.spawn("w1", [sys.executable, str(WORKERS_DIR / "worker_sleep.py"), "0.1", "w1"])
            pool.spawn("w2", [sys.executable, str(WORKERS_DIR / "worker_sleep.py"), "30", "w2"])
            mid = _live_descendant_pids(os.getpid())
            self.assertTrue(leaked_pids(before, mid),
                             "workers are running right now -- this must not be empty")
            pool.close()
        after = _live_descendant_pids(os.getpid())
        self.assertEqual(leaked_pids(before, after), frozenset())


if __name__ == "__main__":
    unittest.main()
