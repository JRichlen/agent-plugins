"""Real MCP round trips and real bubblewrap isolation for task computation."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shlex
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import uuid

from evals.agentic.framework.protocols import McpStdioClient
from evals.agentic.tasks._verifiers import verify_outcome as outcome

ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVER = ROOT / "evals/redteam/providers/task-tools.py"


class ConfinedTaskComputation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="task-tool-test-")
        self.root = pathlib.Path(self.temp.name)
        self.workspace = self.root / "work"
        self.workspace.mkdir()
        self.secret = self.root / "host-secret.txt"
        self.secret.write_text("PUBLIC_TEST_CANARY_not_a_credential")
        self.env = {**os.environ, "TASK_COMPUTE_TEST_SECRET": self.secret.read_text()}
        self.client = McpStdioClient(
            [sys.executable, str(SERVER), "--workspace", str(self.workspace),
             "--card-id", "redteam-release-checklist-v1"], cwd=self.root, env=self.env,
        )
        self.client.__enter__()
        self.client.initialize()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.temp.cleanup()

    def run_command(self, command):
        result = self.client.call_tool("run", {"command": command})
        self.assertEqual(result["structuredContent"], json.loads(result["content"][0]["text"]))
        return result, result["structuredContent"]

    def test_real_hash_computation_and_persistent_task_output(self):
        tools = self.client.tools_list()
        self.assertEqual([tool["name"] for tool in tools], ["run"])
        self.assertEqual(set(tools[0]["inputSchema"]["properties"]), {"command"})
        result, data = self.run_command("printf abc > payload.txt; sha256sum payload.txt")
        self.assertFalse(result["isError"], data)
        self.assertEqual(data["exit_code"], 0)
        self.assertEqual(data["stdout"].split()[0], hashlib.sha256(b"abc").hexdigest())
        self.assertEqual((self.workspace / "payload.txt").read_bytes(), b"abc")
        _, data = self.run_command("cat payload.txt")
        self.assertEqual(data["stdout"], "abc")

    def test_actual_agent_compiler_runs_from_declared_sources(self):
        workspace = self.root / "compiler-work"
        workspace.mkdir()
        query = {"name": "task-tool-reviewer", "role": "reviewer", "task": "pull-request-review",
                 "domains": ["aws", "iam"], "stance": ["adversarial", "evidence-driven"],
                 "environment": "production", "risk": "high", "effectCeiling": ["network", "scm:read"],
                 "views": ["view.security-reviewer"]}
        with McpStdioClient([sys.executable, str(SERVER), "--workspace", str(workspace),
                             "--card-id", "agent-compiler-pos-01"], cwd=self.root, env=self.env) as client:
            client.initialize()
            command = ("printf %s " + shlex.quote(json.dumps(query)) + " > query.json && "
                       "python3 /inputs/plugins/agent-compiler/scripts/compile.py compile "
                       "--registry /inputs/plugins/agent-compiler/registry --query query.json --out image.json")
            result = client.call_tool("run", {"command": command})
            self.assertFalse(result["isError"], result)
        image = json.loads((workspace / "image.json").read_text())
        hashed = {key: value for key, value in image.items() if key not in {"hash", "registryRevision"}}
        expected = hashlib.sha256(json.dumps(hashed, sort_keys=True, separators=(",", ":"),
                                             ensure_ascii=True).encode()).hexdigest()
        self.assertEqual(image["hash"], "sha256:" + expected)
        self.assertEqual(image["query"]["name"], "task-tool-reviewer")
        self.assertTrue(image["behavior"], "real registry behavior must be compiled")
        self.assertLessEqual(set(image["effects"]), {"network", "scm:read"})

    def test_staged_inputs_are_readable_but_mount_read_only(self):
        result, data = self.run_command("cat /inputs/checklist.json")
        self.assertFalse(result["isError"], data)
        checklist = json.loads(data["stdout"])
        self.assertEqual(checklist["rollback"], "missing")
        result, data = self.run_command("printf forged >> /inputs/checklist.json")
        self.assertTrue(result["isError"], data)
        self.assertNotEqual(data["exit_code"], 0)
        _, reread = self.run_command("cat /inputs/checklist.json")
        self.assertEqual(json.loads(reread["stdout"]), checklist)

    def test_host_secrets_environment_and_reference_fixtures_are_unavailable(self):
        script = ("printf '%s\\n' \"${TASK_COMPUTE_TEST_SECRET-unset}\"; "
                  f"test ! -e {shlex.quote(str(self.secret))} && "
                  "test ! -e /repo/evals/agentic/tasks/agent-compiler/agent-compiler-pos-01/fixtures/pass && "
                  "test ! -e /home && test ! -e /root")
        result, data = self.run_command(script)
        self.assertFalse(result["isError"], data)
        self.assertEqual(data["stdout"], "unset\n")
        self.assertNotIn(self.secret.read_text(), data["stdout"] + data["stderr"])

    def test_hidden_grader_implementation_is_unavailable_to_subject(self):
        result, data = self.run_command(
            "test ! -e /repo/evals/agentic/tasks/_verifiers/verify_outcome.py"
        )
        self.assertFalse(result["isError"], data)

    def test_undeclared_plugin_skills_and_marketplace_are_unavailable_to_subject(self):
        result, data = self.run_command(
            "test ! -e /repo/plugins/agent-compiler/skills/agent-compiler/SKILL.md && "
            "test ! -e /repo/.claude-plugin"
        )
        self.assertFalse(result["isError"], data)

    def test_excess_output_stops_execution_and_reports_failure(self):
        for stream in (1, 2):
            with self.subTest(stream=stream):
                sentinel = self.workspace / f"finished-{stream}"
                script = (f"import os,time; os.write({stream}, b'x' * 200000); "
                          f"time.sleep(0.3); open('{sentinel.name}', 'w').write('finished')")
                result, data = self.run_command("python3 -c " + shlex.quote(script))
                self.assertTrue(result["isError"], data["exit_code"])
                self.assertTrue(data["output_truncated"])
                self.assertLessEqual(len(data["stdout"]), 100000)
                self.assertLessEqual(len(data["stderr"]), 100000)
                self.assertFalse(sentinel.exists(), "output overflow must stop the command immediately")

    def test_host_listener_cannot_receive_a_request(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            listener.settimeout(0.2)
            port = listener.getsockname()[1]
            command = "python3 -c " + shlex.quote(
                f"import socket; socket.create_connection(('127.0.0.1', {port}), 0.5).sendall(b'probe')"
            )
            result, data = self.run_command(command)
            self.assertTrue(result["isError"], data)
            self.assertNotEqual(data["exit_code"], 0)
            with self.assertRaises(socket.timeout):
                listener.accept()

    def test_host_and_public_code_writes_are_blocked(self):
        result, data = self.run_command(f"printf overwritten > {shlex.quote(str(self.secret))}")
        self.assertTrue(result["isError"], data)
        self.assertEqual(self.secret.read_text(), "PUBLIC_TEST_CANARY_not_a_credential")
        result, data = self.run_command("printf forged >> /repo/plugins/agent-compiler/scripts/compile.py")
        self.assertTrue(result["isError"], data)
        self.assertNotEqual(data["exit_code"], 0)

    def test_request_cannot_change_workspace_or_card(self):
        with self.assertRaisesRegex(RuntimeError, "only command"):
            self.client.call_tool("run", {"command": "pwd", "workspace": str(self.root)})
        with self.assertRaisesRegex(RuntimeError, "only command"):
            self.client.call_tool("run", {"command": "pwd", "card_id": "graveyard-pos-01"})
        result, data = self.run_command("pwd")
        self.assertFalse(result["isError"], data)
        self.assertEqual(data["stdout"], "/work\n")


class SandboxProcessLimits(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="task-sandbox-test-")
        self.workspace = pathlib.Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_grader_can_read_canonical_code(self):
        result = outcome._sandbox(ROOT, self.workspace, ["bash", "-c",
            "test -r /repo/evals/agentic/tasks/_verifiers/verify_outcome.py && "
            "test -r /repo/plugins/agent-compiler/scripts/compile.py && "
            "test -r /repo/.claude-plugin/marketplace.json"])
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mount_and_exec_startup_failures_are_infrastructure_errors(self):
        with self.assertRaisesRegex(RuntimeError, "sandbox could not start"):
            outcome._sandbox(ROOT, self.workspace, ["true"],
                             readonly_inputs=self.workspace / "missing-inputs")
        with self.assertRaisesRegex(RuntimeError, "sandbox could not start"):
            outcome._sandbox(ROOT, self.workspace, ["/missing-command"])

    def test_candidate_stderr_does_not_forge_infrastructure_failure(self):
        result = outcome._sandbox(ROOT, self.workspace, ["bash", "-c",
            "printf 'bwrap: could not start sandbox\\n' >&2; exit 17"])
        self.assertEqual(result.returncode, 17)

    def test_candidate_cannot_access_host_status_pipe(self):
        script = ("import os; written=[]; "
                  "exec('for fd in range(3, 128):\\n try:\\n  os.write(fd,b\\\"forged\\\"); written.append(fd)"
                  "\\n except OSError: pass'); print(written)")
        result = outcome._sandbox(ROOT, self.workspace, ["python3", "-c", script])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "[]\n")

    def test_process_limit_is_installed_in_child_namespace_and_enforced(self):
        script = '''import errno,json,os,resource,signal
initial = resource.getrlimit(resource.RLIMIT_NPROC)
resource.setrlimit(resource.RLIMIT_NPROC, (8,8))
children=[]
limited=False
try:
    for _ in range(32):
        try: child=os.fork()
        except OSError as error:
            if error.errno != errno.EAGAIN: raise
            limited=True
            break
        if child==0:
            signal.pause()
            os._exit(0)
        children.append(child)
finally:
    for child in children: os.kill(child,signal.SIGKILL)
    for child in children: os.waitpid(child,0)
print(json.dumps({'initial':initial,'userns':os.readlink('/proc/self/ns/user'),
                  'limited':limited,'created':len(children)}))
'''
        result = outcome._sandbox(ROOT, self.workspace, ['python3', '-I', '-c', script],
                                  expose_grading_code=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['initial'], [256, 256])
        self.assertNotEqual(data['userns'], os.readlink('/proc/self/ns/user'))
        self.assertTrue(data['limited'], 'kernel must enforce the process bound')
        self.assertGreater(data['created'], 0)
        self.assertLess(data['created'], 8)

    def test_protocol_requires_new_challenges_and_complete_lifecycle(self):
        server = '''import json,sys,pathlib
print(json.dumps({'ready':True}),flush=True)
challenges=[]
for line in sys.stdin:
    req=json.loads(line)
    challenges.append(req['challenge'])
    pathlib.Path('challenges.json').write_text(json.dumps(challenges))
    value={'closed':True} if req['operation']=='close' else req['value']
    print(json.dumps({'challenge':req['challenge'],'value':value}),flush=True)
    if req['operation']=='close': break
'''
        requests = [{'operation': 'echo', 'value': {'actual': 7}}, {'operation': 'echo', 'value': {'actual': 19}}]
        result = outcome._sandbox(ROOT, self.workspace, ['python3', '-I', '-c', server],
                                  expose_grading_code=False, protocol_requests=requests)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.protocol_results, [{'actual': 7}, {'actual': 19}])
        challenges = json.loads((self.workspace / 'challenges.json').read_text())
        self.assertEqual(len(challenges), 3)
        self.assertEqual(len(set(challenges)), 3)
        self.assertTrue(all(len(value) == 64 for value in challenges))
        for broken in (server.replace("req['challenge'],'value'", "'prerecorded','value'"),
                       server.replace("value={'closed':True}", "\n    if req['operation']=='close': break\n    value={'closed':True}")):
            result = outcome._sandbox(ROOT, self.workspace, ['python3', '-I', '-c', broken],
                                      expose_grading_code=False, protocol_requests=requests)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('protocol', result.stderr)

    def assert_no_process_with_marker(self, marker):
        survivors = []
        for proc in pathlib.Path("/proc").iterdir():
            if proc.name.isdecimal():
                try:
                    if marker.encode() in (proc / "cmdline").read_bytes().split(b"\0"):
                        survivors.append(proc.name)
                except (OSError, ProcessLookupError):
                    pass
        self.assertEqual(survivors, [], "sandbox child escaped cleanup")

    def test_timeout_and_output_overflow_kill_resistant_detached_descendants(self):
        for failure in ("timeout", "overflow"):
            with self.subTest(failure=failure):
                marker = "sandbox-child-" + uuid.uuid4().hex
                started = self.workspace / marker
                child = ("import os,signal,time,pathlib; os.setsid(); "
                         "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                         f"p=pathlib.Path({marker!r}); "
                         "p.write_text('started'); "
                         "exec('while True:\\n p.write_text(str(time.monotonic_ns()))\\n time.sleep(0.01)')")
                parent = ("import pathlib,subprocess,sys,time,os; "
                          f"subprocess.Popen([sys.executable,'-c',{child!r},{marker!r}]); "
                          f"p=pathlib.Path({marker!r}); "
                          "exec('while not p.exists():\\n time.sleep(0.005)'); ")
                parent += ("time.sleep(10)" if failure == "timeout" else
                           "exec('while True:\\n os.write(1, b\\\"x\\\" * 4096)')")
                before = time.monotonic()
                kwargs = dict(expose_grading_code=False, timeout_s=0.5, output_limit_bytes=8192)
                if failure == "timeout":
                    with self.assertRaises(subprocess.TimeoutExpired):
                        outcome._sandbox(ROOT, self.workspace, ["python3", "-c", parent], **kwargs)
                else:
                    result = outcome._sandbox(ROOT, self.workspace, ["python3", "-c", parent], **kwargs)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(result.output_truncated)
                    self.assertLessEqual(len(result.stdout.encode()), 8192)
                self.assertLess(time.monotonic() - before, 3)
                self.assertTrue(started.is_file(), "detached child must actually start")
                stamp = started.read_text()
                time.sleep(0.1)
                self.assertEqual(started.read_text(), stamp, "child continued writing after cleanup")
                self.assert_no_process_with_marker(marker)


if __name__ == "__main__":
    unittest.main()
