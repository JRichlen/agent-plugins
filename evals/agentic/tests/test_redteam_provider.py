"""Red-team lane tests: T42 (pinned version + offline config validity) and
T43 (custom-provider API conformance), design §§2-3, §13.

These are REAL-FIXTURE tests: they shell out to the pinned promptfoo 0.122.0
binary by path (never `npx`) with the lane's offline environment, exactly as
`evals/redteam/run.sh` does. No network, no model call.
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
REDTEAM_ROOT = REPO_ROOT / "evals" / "redteam"
PROMPTFOO_SH = REDTEAM_ROOT / "bin" / "promptfoo.sh"
PINNED_VERSION = "0.122.0"


def _offline_env(tmp_home: pathlib.Path, extra: dict | None = None) -> dict:
    env = dict(os.environ)
    env.update({
        "HOME": str(tmp_home / "home"),
        "CODEX_HOME": str(tmp_home / "no-codex"),
        "PROMPTFOO_CONFIG_DIR": str(tmp_home / "pfhome"),
    })
    (tmp_home / "home").mkdir(parents=True, exist_ok=True)
    (tmp_home / "no-codex").mkdir(parents=True, exist_ok=True)
    (tmp_home / "pfhome").mkdir(parents=True, exist_ok=True)
    if extra:
        env.update(extra)
    return env


def _run(args: list[str], env: dict, cwd: pathlib.Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        args, env=env, cwd=str(cwd or REPO_ROOT),
        capture_output=True, text=True, timeout=60,
    )


def _iter_configs() -> list[pathlib.Path]:
    out = []
    for p in REDTEAM_ROOT.rglob("*.yaml"):
        rel = p.relative_to(REDTEAM_ROOT)
        parts = rel.parts
        if parts[0] == ".artifacts":
            continue
        if "hosted" in parts or "paid" in parts:
            continue
        out.append(p)
    return sorted(out)


class PinnedVersionAndConfigValidity(unittest.TestCase):
    """T42: the wrapper reports the pinned version, and every config under
    evals/redteam/** validates against promptfoo 0.122.0's own schema."""

    def test_wrapper_reports_pinned_version_and_validates_every_config(self):
        with tempfile.TemporaryDirectory() as td:
            env = _offline_env(pathlib.Path(td))
            result = _run([str(PROMPTFOO_SH), "--version"], env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), PINNED_VERSION)

            configs = _iter_configs()
            self.assertGreaterEqual(
                len(configs), 6,
                "expected at least the 6 part-1 configs (root, offline-stub, "
                "3 controls, canary-egress)",
            )
            for cfg in configs:
                with self.subTest(config=str(cfg)):
                    result = _run(
                        [str(PROMPTFOO_SH), "validate", "-c", str(cfg)], env=env,
                    )
                    self.assertEqual(
                        result.returncode, 0,
                        f"{cfg} failed to validate:\n{result.stdout}\n{result.stderr}",
                    )

    def test_wrapper_reports_pinned_version_and_validates_every_config__negative(self):
        """Catalog sibling (contract §7.4 item 4). Points PROMPTFOO_HOME at
        fixtures/counterfeit/fake-promptfoo-wrong-version (T42's
        negative_control): a fake install claiming 0.123.0. The wrapper must
        refuse it with 'version drift' BEFORE ever exec'ing the (symlinked,
        otherwise-real) entrypoint -- proving check 2 is a real gate and not
        a check that only fires when the whole install is absent."""
        fake_home = REDTEAM_ROOT / "fixtures" / "counterfeit" / "fake-promptfoo-wrong-version"
        self.assertTrue(fake_home.is_dir(), f"negative_control fixture missing: {fake_home}")
        with tempfile.TemporaryDirectory() as td:
            env = _offline_env(pathlib.Path(td), extra={"PROMPTFOO_HOME": str(fake_home)})
            result = _run([str(PROMPTFOO_SH), "--version"], env=env)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("version drift", result.stderr)
            self.assertIn("0.123.0", result.stderr)


class ProviderApiConformance(unittest.TestCase):
    """T43: promptfoo itself loads and calls providers/stub-echo.js and
    providers/target-textual.js via file:// references during a real offline
    eval against configs/offline-stub.yaml."""

    def test_promptfoo_actually_invokes_the_custom_provider(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            sidechannel_dir = tmp / "sidechannel"
            ledger_dir = tmp / "ledger"
            sidechannel_dir.mkdir()
            ledger_dir.mkdir()
            env = _offline_env(tmp, extra={
                "REDTEAM_SIDECHANNEL_DIR": str(sidechannel_dir),
                "REDTEAM_LEDGER_DIR": str(ledger_dir),
            })
            out_path = tmp / "results.json"
            result = _run(
                [str(PROMPTFOO_SH), "eval", "-c", str(REDTEAM_ROOT / "configs" / "offline-stub.yaml"),
                 "--no-cache", "--no-write", "--no-table", "--no-progress-bar",
                 "-o", str(out_path)],
                env=env,
            )
            # promptfoo's default exit code convention: 100 = "the eval
            # completed but some row failed/errored" (design §8.4). Both 0
            # and 100 mean "the eval actually ran".
            self.assertIn(result.returncode, (0, 100), result.stdout + result.stderr)

            # THE side-effect proof (design E2/§13): stub-echo.js really ran.
            side_files = list(sidechannel_dir.iterdir())
            self.assertEqual(
                len(side_files), 1,
                "stub-echo.js's callApi should have written exactly one side-channel file",
            )
            content = side_files[0].read_text(encoding="utf-8")
            self.assertIn("conformance probe", content)

            self.assertTrue(out_path.is_file())
            data = json.loads(out_path.read_text(encoding="utf-8"))
            rows = (data.get("results") or {}).get("results") or data.get("results") or []
            self.assertEqual(len(rows), 2, "offline-stub.yaml declares 2 providers x 1 test")

            by_label = {r["provider"]["label"]: r for r in rows}
            self.assertIn("stub-echo", by_label)
            self.assertIn("target-textual-throw", by_label)

            echo_row = by_label["stub-echo"]
            self.assertTrue(echo_row["success"])
            self.assertTrue(echo_row["response"]["output"].startswith("echo: "))
            self.assertIn("tokenUsage", echo_row["response"])

    def test_promptfoo_actually_invokes_the_custom_provider__negative(self):
        """Catalog sibling. negative_control (design §3.2): a plain-object
        export is NOT a constructor and must fail to load, never silently
        produce a passing row. Uses a small dedicated fixture module, since
        the real providers in evals/redteam/providers/** are all correctly
        class-shaped by construction and cannot demonstrate this failure."""
        fixture_dir = REDTEAM_ROOT / "fixtures" / "counterfeit"
        plain_object_provider = fixture_dir / "plain-object-provider.js"
        self.assertTrue(plain_object_provider.is_file(),
                         f"negative_control fixture missing: {plain_object_provider}")
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            env = _offline_env(tmp)
            cfg = tmp / "plain-object.yaml"
            cfg.write_text(f"""
description: "T43 negative control: plain-object export"
prompts:
  - "hello"
providers:
  - id: file://{plain_object_provider}
    label: plain-object
tests:
  - vars: {{}}
""", encoding="utf-8")
            out_path = tmp / "out.json"
            result = _run(
                [str(PROMPTFOO_SH), "eval", "-c", str(cfg),
                 "--no-cache", "--no-write", "--no-table", "--no-progress-bar",
                 "-o", str(out_path)],
                env=env,
            )
            # A naive shape-only check would accept this file (it "exports
            # the right keys"). Only actually letting promptfoo load it (via
            # `new`) proves the failure this control exists to catch.
            combined = result.stdout + result.stderr
            self.assertNotEqual(result.returncode, 0)
            self.assertTrue(
                "not a constructor" in combined or "is not a function" in combined,
                f"expected a constructor-shaped load failure, got:\n{combined}",
            )


class ProviderErrorIsFault(unittest.TestCase):
    """T43 continued: a provider that throws yields failureReason == 2,
    classified FAULT -- never a silent pass."""

    def test_throwing_provider_is_classified_fault_not_pass(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            ledger_dir = tmp / "ledger"
            sidechannel_dir = tmp / "sidechannel"
            ledger_dir.mkdir()
            sidechannel_dir.mkdir()
            env = _offline_env(tmp, extra={
                "REDTEAM_LEDGER_DIR": str(ledger_dir),
                "REDTEAM_SIDECHANNEL_DIR": str(sidechannel_dir),
            })
            out_path = tmp / "results.json"
            _run(
                [str(PROMPTFOO_SH), "eval", "-c", str(REDTEAM_ROOT / "configs" / "offline-stub.yaml"),
                 "--no-cache", "--no-write", "--no-table", "--no-progress-bar",
                 "-o", str(out_path)],
                env=env,
            )
            data = json.loads(out_path.read_text(encoding="utf-8"))
            rows = (data.get("results") or {}).get("results") or data.get("results") or []
            by_label = {r["provider"]["label"]: r for r in rows}
            throw_row = by_label["target-textual-throw"]
            self.assertFalse(throw_row["success"])
            self.assertEqual(throw_row.get("failureReason"), 2, throw_row)

    def test_throwing_provider_is_classified_fault_not_pass__negative(self):
        """Catalog sibling. negative_control: the SAME config's stub-echo
        row, which must NOT be classified FAULT (failureReason 0, a real
        pass) -- proving the FAULT classification is specific to the
        throwing row, not a blanket 'everything in this config is a fault'
        artifact of the harness."""
        cfg = REDTEAM_ROOT / "configs" / "offline-stub.yaml"
        self.assertTrue(cfg.is_file(), f"negative_control fixture missing: {cfg}")
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            ledger_dir = tmp / "ledger"
            sidechannel_dir = tmp / "sidechannel"
            ledger_dir.mkdir()
            sidechannel_dir.mkdir()
            env = _offline_env(tmp, extra={
                "REDTEAM_LEDGER_DIR": str(ledger_dir),
                "REDTEAM_SIDECHANNEL_DIR": str(sidechannel_dir),
            })
            out_path = tmp / "results.json"
            _run(
                [str(PROMPTFOO_SH), "eval", "-c", str(cfg),
                 "--no-cache", "--no-write", "--no-table", "--no-progress-bar",
                 "-o", str(out_path)],
                env=env,
            )
            data = json.loads(out_path.read_text(encoding="utf-8"))
            rows = (data.get("results") or {}).get("results") or data.get("results") or []
            by_label = {r["provider"]["label"]: r for r in rows}
            echo_row = by_label["stub-echo"]
            self.assertTrue(echo_row["success"])
            self.assertNotEqual(echo_row.get("failureReason"), 2)


class ClassExportRequired(unittest.TestCase):
    """T43's own negative-control test named as its own catalog entry is
    exercised inline as ProviderApiConformance's __negative sibling above;
    this class documents the design-cited rule directly against the source
    (design §3.2's 'correction to a prior document') so the rule is checked
    even without spawning promptfoo."""

    def test_real_providers_all_export_a_class_not_a_plain_object(self):
        providers_dir = REDTEAM_ROOT / "providers"
        js_files = [p for p in providers_dir.glob("*.js")]
        self.assertGreater(len(js_files), 0)
        for p in js_files:
            with self.subTest(provider=str(p)):
                text = p.read_text(encoding="utf-8")
                self.assertIn("module.exports = ", text)
                self.assertRegex(
                    text, r"class \w+", f"{p} does not appear to export a class",
                )

    def test_real_providers_all_export_a_class_not_a_plain_object__negative(self):
        fixture = REDTEAM_ROOT / "fixtures" / "counterfeit" / "plain-object-provider.js"
        self.assertTrue(fixture.is_file(), f"negative_control fixture missing: {fixture}")
        text = fixture.read_text(encoding="utf-8")
        # The fixture must NOT satisfy the class-shape check -- proving this
        # static check discriminates the real providers from the fixture at
        # all, rather than passing everything it looks at.
        self.assertNotRegex(text, r"class \w+")


if __name__ == "__main__":
    unittest.main()
