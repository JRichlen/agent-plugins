"""Execute actual generator bodies with Windows-style text writers; no browser."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LF_STDOUT = 'sys.stdout.reconfigure(encoding="utf-8", newline="\\n")'
WINDOWS_STDOUT = 'import io, sys\nsys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\\r\\n")\n'
WINDOWS_FILES = '''import builtins
original_open = builtins.open
def windows_open(file, mode="r", *args, **kwargs):
    if ("w" in mode or "a" in mode) and "b" not in mode and kwargs.get("newline") is None:
        kwargs["newline"] = "\\r\\n"
    return original_open(file, mode, *args, **kwargs)
builtins.open = windows_open
'''


def body(path):
    return (ROOT / path).read_text(encoding="utf-8").split("<<'PY'\n", 1)[1].split("\nPY\n", 1)[0]


def execute(program, arguments, prefix=WINDOWS_STDOUT):
    with tempfile.TemporaryDirectory(prefix="renderer-emulation-") as folder:
        script = Path(folder) / "renderer.py"
        script.write_text(prefix + program, encoding="utf-8", newline="\n")
        return subprocess.run([sys.executable, str(script), *map(str, arguments)], capture_output=True, check=True).stdout


class RendererControls(unittest.TestCase):
    def test_generators_force_lf_even_with_windows_stdout(self):
        for source, output in (("docs/build-examples.sh", "docs/examples/index.html"), ("docs/build-index.sh", "docs/index.html")):
            with self.subTest(source=source):
                program = body(source)
                self.assertIn(LF_STDOUT, program)
                result = execute(program, [ROOT])
                self.assertNotIn(b"\r\n", result)
                self.assertEqual(result, (ROOT / output).read_bytes())
                # This control must detect losing the actual writer override.
                self.assertIn(b"\r\n", execute(program.replace(LF_STDOUT, "", 1), [ROOT]))

    def test_regular_and_attested_capture_keep_criteria_and_different_inputs(self):
        with tempfile.TemporaryDirectory(prefix="ordinary-capture-render-") as folder:
            root = Path(folder)
            data_dir = root / "docs/examples/data"
            data_dir.mkdir(parents=True)
            shutil.copytree(ROOT / "docs/_shared", root / "docs/_shared")
            original = json.loads((ROOT / "docs/examples/data/stop-rule.json").read_text(encoding="utf-8"))
            for attestation in ("none", "github-fixture-only"):
                original["provenance"].update(source="promptfoo", attestation=attestation)
                (data_dir / "stop-rule.json").write_text(json.dumps(original), encoding="utf-8", newline="\n")
                rendered = execute(body("docs/build-examples.sh"), [root]).decode("utf-8")
                self.assertIn("Inputs differ:", rendered)
                self.assertIn("Per-arm criteria and context", rendered)
                self.assertIn("Original source config", rendered)

    def test_capture_json_forces_lf_with_windows_default_file_writer(self):
        with tempfile.TemporaryDirectory(prefix="capture-writer-") as folder:
            root = Path(folder)
            (root / "promptfooconfig.yaml").write_text("defaultTest:\n  options:\n    provider:\n      id: anthropic:messages:claude-test\n", encoding="utf-8", newline="\n")
            rows = [{"vars": {"skill": skill, "question": "same"}, "provider": {"id": "openrouter:qwen/test"}, "response": {"output": "fixture"}, "success": True} for skill in ("real", "calibration")]
            results = root / "results.json"
            results.write_text(json.dumps({"results": {"results": rows}}), encoding="utf-8", newline="\n")
            program = body("evals/paid/capture-example.sh")
            for mutant in (False, True):
                output = root / str(mutant)
                output.mkdir()
                selected = program.replace('newline="\\n"', "newline=None") if mutant else program
                execute(selected, [results, "test", output, "a" * 40, "unknown", "", "none", root], WINDOWS_FILES)
                snapshot = (output / "test.json").read_bytes()
                self.assertEqual(b"\r\n" in snapshot, mutant)
