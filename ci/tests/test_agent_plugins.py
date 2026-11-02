import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("agent_plugins", ROOT / "ci/agent_plugins.py")
agent_plugins = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_plugins)


def quiet(argv):
    with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()):
        code = agent_plugins.main(argv)
    return code, out.getvalue()


def fixture(folder: Path, manifest: dict) -> Path:
    (folder / ".claude-plugin").mkdir()
    (folder / ".claude-plugin/marketplace.json").write_text(json.dumps(
        {"name": "m", "plugins": [{"name": manifest["name"], "source": "./plugins/" + manifest["name"]}]}))
    plugin = folder / "plugins" / manifest["name"] / ".claude-plugin"
    plugin.mkdir(parents=True)
    (plugin / "plugin.json").write_text(json.dumps(manifest))
    return plugin.parent


class AgentPluginsProjection(unittest.TestCase):
    def test_real_repository_is_in_sync(self):
        self.assertEqual(quiet(["--root", str(ROOT), "--check"])[0], 0)

    def test_closed_manifest_drops_claude_component_paths(self):
        result = agent_plugins.manifest({"name": "a.b-c", "version": "1", "skills": "./skills/",
                                         "commands": "./commands/", "mcpServers": {}})
        self.assertEqual(result, {"$schema": agent_plugins.PLUGIN_SCHEMA, "name": "a.b-c", "version": "1"})

    def test_invalid_names_and_metadata_are_rejected(self):
        for name in ("Upper", "-start", "end-", "has--double", "dots..x", "", "x" * 65, 7):
            with self.assertRaises(ValueError, msg=name):
                agent_plugins.manifest({"name": name})
        for bad in ({"author": {"name": "a", "role": "b"}}, {"author": {"name": 1}},
                    {"keywords": "one"}, {"license": ["MIT"]}):
            with self.assertRaises(ValueError, msg=bad):
                agent_plugins.manifest({"name": "ok", **bad})

    def test_stdio_server_maps_placeholders_and_rejects_shell_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            plugin = Path(folder).resolve()
            mapped = agent_plugins.server(plugin, "k", {"command": "python3", "args": ["${CLAUDE_PLUGIN_ROOT}/s.py"],
                                                        "env": {"D": "${CLAUDE_PLUGIN_DATA}/x"},
                                                        "cwd": "${CLAUDE_PLUGIN_DATA}/cache"}, "t")
            self.assertEqual(mapped, {"type": "stdio", "command": "python3", "args": ["${PLUGIN_ROOT}/s.py"],
                                      "env": {"D": "${PLUGIN_DATA}/x"}, "cwd": "${PLUGIN_DATA}/cache"})
            for entry in ({"command": "${CLAUDE_PLUGIN_ROOT}/bin"}, {"command": "node server.js"},
                          {"command": "bin/server"}, {"command": "x", "args": ["${CLAUDE_PROJECT_DIR}"]},
                          {"command": "x", "cwd": "data"}, {"command": "x", "timeout": 5},
                          {"type": "ws", "url": "wss://x"}):
                with self.assertRaises(ValueError, msg=entry):
                    agent_plugins.server(plugin, "k", entry, "t")

    def test_package_paths_and_reserved_env_fail_containment(self):
        with tempfile.TemporaryDirectory() as folder:
            plugin = Path(folder).resolve() / "plugin"
            plugin.mkdir()
            for entry in ({"command": "./../outside/server"}, {"command": "x", "cwd": "./../up"},
                          {"command": "x", "cwd": "${PLUGIN_ROOT}/../up"}, {"command": "x", "cwd": "${PLUGIN_DATA}/../up"},
                          {"command": "x", "env": {"PLUGIN_ROOT": "o"}}, {"command": "x", "env": {"plugin_data": "o"}},
                          {"command": "x", "env": {"": "o"}}):
                with self.assertRaises(ValueError, msg=entry):
                    agent_plugins.server(plugin, "k", entry, "t")
            try:
                (plugin / "link").symlink_to(plugin.parent, target_is_directory=True)
            except OSError:
                pass  # Windows without symlink privilege; the lexical cases above still run.
            else:
                with self.assertRaises(ValueError):
                    agent_plugins.server(plugin, "k", {"command": "./link/server"}, "t")
            ok = agent_plugins.server(plugin, "k", {"command": "./bin/s", "cwd": "${PLUGIN_ROOT}/data"}, "t")
            self.assertEqual(ok["cwd"], "${PLUGIN_ROOT}/data")

    def test_remote_url_and_headers_follow_section_7_2_1(self):
        plugin = Path(".")
        for url in ("http://example.com/mcp", "http://localhost.evil.example/mcp", "http://localhost＠evil.example/mcp",
                    "http://localhost@evil.example/mcp", "https://user:pw@example.com/mcp", "https://example.com/mcp#x",
                    "ftp://example.com", "https:///mcp", "https://example.com/${TOKEN}"):
            with self.assertRaises(ValueError, msg=url):
                agent_plugins.server(plugin, "k", {"type": "http", "url": url}, "t")
        for url in ("https://example.com/mcp", "http://localhost:8080/mcp", "http://127.0.0.2/mcp", "http://[::1]/mcp"):
            self.assertEqual(agent_plugins.server(plugin, "k", {"type": "http", "url": url}, "t")["url"], url)
        for headers in (["invalid"], {"X-Tenant": "a", "x-tenant": "b"}, {"Bad Name": "v"}, {"X": "a\r\nInjected: 1"}, {"X": 1}):
            with self.assertRaises(ValueError, msg=headers):
                agent_plugins.server(plugin, "k", {"type": "sse", "url": "https://e.com", "headers": headers}, "t")
        self.assertEqual(agent_plugins.server(plugin, "k", {"type": "sse", "url": "https://e.com",
                                                            "headers": {"X-Tenant": "a"}}, "t")["type"], "sse")

    def test_check_reports_drift_and_unexpected_files_then_write_repairs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            plugin = fixture(root, {"name": "demo", "version": "0.1.0", "skills": "./skills/"})
            code, _ = quiet(["--root", str(root), "--check"])
            self.assertEqual(code, 1)
            (plugin / "mcp.json").write_text("{}")
            self.assertEqual(quiet(["--root", str(root)])[0], 0)
            self.assertFalse((plugin / "mcp.json").exists())
            self.assertEqual(json.loads((plugin / "plugin.json").read_text())["name"], "demo")
            self.assertEqual(quiet(["--root", str(root), "--check"])[0], 0)
            (plugin / "plugin.json").write_text((plugin / "plugin.json").read_text().replace("0.1.0", "9"))
            self.assertEqual(quiet(["--root", str(root), "--check"])[0], 1)

    def test_crlf_checkout_is_not_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            plugin = fixture(root, {"name": "demo"})
            quiet(["--root", str(root)])
            path = plugin / "plugin.json"
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
            self.assertEqual(quiet(["--root", str(root), "--check"])[0], 0)

    def test_skills_follow_the_agent_skills_spec(self):
        good = ('---\nname: demo\ndescription: >-\n  Does a thing.\nlicense: MIT\nallowed-tools: Bash Read\n'
                'metadata:\n  argument-hint: "[date]"\n  user-invocable: "true"\n---\nbody\n')
        bad = {"unknown field": good.replace("license: MIT", "user-invocable: true"),
               "string": good.replace("allowed-tools: Bash Read", "allowed-tools:\n  - Bash"),
               "metadata": good.replace('user-invocable: "true"', "user-invocable: true"),
               "directory": good.replace("name: demo", "name: other"),
               "kebab": good.replace("name: demo", "name: Demo"),
               "1-1024": good.replace("Does a thing.", "x" * 1025),
               "1-500": good.replace("license: MIT", "compatibility: " + "x" * 501),
               "mapping": "no frontmatter\n"}
        with tempfile.TemporaryDirectory() as folder:
            skill = Path(folder) / "demo" / "SKILL.md"
            skill.parent.mkdir()
            skill.write_bytes(good.replace("\n", "\r\n").encode("utf-8"))
            agent_plugins.check_skill(skill, "t")
            for expected, text in bad.items():
                skill.write_text(text, encoding="utf-8")
                with self.assertRaisesRegex(ValueError, expected):
                    agent_plugins.check_skill(skill, "t")

    def test_fallback_parser_matches_pyyaml_on_every_repository_skill(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML unavailable; the fallback is exercised by the next test")
        skills = sorted(ROOT.glob("plugins/*/skills/*/SKILL.md"))
        self.assertTrue(skills)
        for skill in skills:
            head = skill.read_text(encoding="utf-8").replace("\r\n", "\n")[4:].partition("\n---\n")[0]
            self.assertEqual(agent_plugins.simple_frontmatter(head), yaml.safe_load(head), skill)

    def test_skill_rules_hold_without_pyyaml(self):
        import builtins
        real_import = builtins.__import__

        def no_yaml(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        builtins.__import__ = no_yaml
        try:
            self.test_skills_follow_the_agent_skills_spec()
            self.assertEqual(quiet(["--root", str(ROOT), "--check"])[0], 0)
        finally:
            builtins.__import__ = real_import

    def test_moved_skills_and_name_mismatch_fail_closed(self):
        for manifest in ({"name": "demo", "skills": "./other/"}, {"name": "renamed"}):
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder).resolve()
                plugin = fixture(root, {"name": "demo"})
                (plugin / ".claude-plugin/plugin.json").write_text(json.dumps(manifest))
                self.assertEqual(quiet(["--root", str(root), "--check"])[0], 2, manifest)


if __name__ == "__main__":
    unittest.main()
