"""Real pinned logger shutdown: buffered records must reach disk before close.

No provider or model is used. These tests exercise the same logger module and
real file transports used by the Promptfoo CLI, without mocking stream events.
"""
from __future__ import annotations

import json
import importlib.util
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[3]
PROVISION = ROOT / "evals/redteam/bin/provision-logger.py"


class PinnedLoggerLifecycle(unittest.TestCase):
    def _run_logger(self, code: str):
        configured = os.environ.get("PROMPTFOO_HOME")
        self.assertTrue(configured, "PROMPTFOO_HOME must identify the provisioned pinned install")
        home = pathlib.Path(configured).resolve()
        self.assertEqual(json.loads((home / "package.json").read_text(encoding="utf-8"))["version"], "0.122.0")
        main = (home / "dist/src/main.js").read_text(encoding="utf-8")
        match = re.search(r'from "(\./logger-[^"/]+\.js)"', main)
        self.assertIsNotNone(match, "pinned CLI must import an identifiable logger module")
        logger_url = (home / "dist/src" / match.group(1)).resolve().as_uri()
        with tempfile.TemporaryDirectory() as td:
            tmp = pathlib.Path(td)
            env = dict(os.environ)
            for key in ("PROMPTFOO_LOG_DIR", "NODE_OPTIONS"):
                env.pop(key, None)
            env.update({
                "HOME": str(tmp), "PROMPTFOO_CONFIG_DIR": str(tmp),
                "PROMPTFOO_DISABLE_DEBUG_LOG": "0", "PROMPTFOO_DISABLE_ERROR_LOG": "0",
                "LOG_LEVEL": "info",
            })
            program = (
                "const loggerModuleUrl = " + json.dumps(logger_url) + ";\n"
                + "import { a as initializeRunLogging, c as logger, n as closeLogger } from "
                + json.dumps(logger_url) + ";\ninitializeRunLogging();\n" + code
            )
            result = subprocess.run(
                ["node", "--input-type=module", "-e", program],
                env=env, capture_output=True, text=True, encoding="utf-8", timeout=10,
            )
            logs = {p.name: p.read_text(encoding="utf-8") for p in (tmp / "logs").glob("*.log")}
        return result, logs

    def test_buffered_messages_all_reach_debug_and_error_files_before_close(self):
        result, logs = self._run_logger("""
for (let i = 0; i < 128; i++) logger.debug(`DEBUG_RECORD_${i} ${'x'.repeat(16384)}`);
for (let i = 0; i < 16; i++) logger.error(`ERROR_RECORD_${i} ${'y'.repeat(16384)}`);
await closeLogger();
process.stdout.write('CLOSE_COMPLETED\\n');
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CLOSE_COMPLETED", result.stdout)
        debug = [text for name, text in logs.items() if name.startswith("promptfoo-debug-")]
        error = [text for name, text in logs.items() if name.startswith("promptfoo-error-")]
        self.assertEqual(len(debug), 1, logs.keys())
        self.assertEqual(len(error), 1, logs.keys())
        self.assertEqual(re.findall(r"DEBUG_RECORD_(\d+) " + "x" * 16384, debug[0]),
                         [str(i) for i in range(128)])
        expected_errors = [str(i) for i in range(16)]
        for text in (debug[0], error[0]):
            self.assertEqual(re.findall(r"ERROR_RECORD_(\d+) " + "y" * 16384, text), expected_errors)
        self.assertNotIn("DEBUG_RECORD_", error[0])

    def test_empty_logger_finishes_with_both_file_transports(self):
        result, logs = self._run_logger("await closeLogger(); process.stdout.write('CLOSE_COMPLETED\\n');")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CLOSE_COMPLETED", result.stdout)
        self.assertEqual(len(logs), 2)
        self.assertTrue(all(text == "" for text in logs.values()), logs)

    def test_filtered_batch_completes_without_hanging_or_logging_rejected_records(self):
        result, logs = self._run_logger("""
const { createRequire } = await import('node:module');
const winston = createRequire(loggerModuleUrl)('winston');
const errorFile = new winston.transports.File({ filename: `${process.env.PROMPTFOO_CONFIG_DIR}/logs/filtered.log`, level: 'error' });
logger.add(errorFile);
errorFile.cork();
for (let i = 0; i < 32; i++) {
  errorFile.write({ level: 'debug', [Symbol.for('level')]: 'debug', message: `REJECTED_${i}` });
  logger.debug(`FILTERED_BATCH_${i}`);
}
errorFile.uncork();
await closeLogger();
process.stdout.write('CLOSE_COMPLETED\\n');
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("CLOSE_COMPLETED", result.stdout)
        debug = next(text for name, text in logs.items() if name.startswith("promptfoo-debug-"))
        error = next(text for name, text in logs.items() if name.startswith("promptfoo-error-"))
        self.assertEqual(re.findall(r"FILTERED_BATCH_(\d+)", debug), [str(i) for i in range(32)])
        self.assertEqual(error, "")
        self.assertEqual(logs["filtered.log"], "")

    def test_actual_file_write_failure_remains_fatal(self):
        self.assertTrue(pathlib.Path("/dev/full").exists(), "Linux /dev/full is required for real ENOSPC")
        result, _ = self._run_logger("""
const { createRequire } = await import('node:module');
const winston = createRequire(loggerModuleUrl)('winston');
logger.add(new winston.transports.File({ filename: '/dev/full', level: 'error' }));
logger.error('ACTUAL_WRITE_FAILURE');
await closeLogger();
process.stdout.write('CLOSE_COMPLETED\\n');
""")
        self.assertNotEqual(result.returncode, 0, "a failed file write must fail the process")
        self.assertIn("ENOSPC", result.stderr)
        self.assertNotIn("CLOSE_COMPLETED", result.stdout)

    def test_real_file_batch_invokes_each_write_callback_once(self):
        result, logs = self._run_logger("""
const { createRequire } = await import('node:module');
const winston = createRequire(loggerModuleUrl)('winston');
const file = new winston.transports.File({
  filename: `${process.env.PROMPTFOO_CONFIG_DIR}/logs/callbacks.log`, level: 'debug',
  format: winston.format.printf(info => info.message),
});
logger.add(file);
const counts = Array(32).fill(0);
file.cork();
for (let i = 0; i < counts.length; i++) file.write({
  level: 'debug', [Symbol.for('level')]: 'debug',
  message: `CALLBACK_RECORD_${i} ${'z'.repeat(16384)}`,
}, () => counts[i]++);
file.uncork();
await closeLogger();
process.stdout.write(`WRITE_CALLBACK_COUNTS=${JSON.stringify(counts)}\\n`);
""")
        self.assertEqual(result.returncode, 0, result.stderr)
        counts = json.loads(result.stdout.split("WRITE_CALLBACK_COUNTS=", 1)[1])
        self.assertEqual(counts, [1] * 32)
        self.assertEqual(re.findall(r"CALLBACK_RECORD_(\d+) " + "z" * 16384, logs["callbacks.log"]),
                         [str(i) for i in range(32)])

    def test_batch_callback_and_formatter_errors_fail_the_real_stream(self):
        for mode in ("callback", "formatter"):
            with self.subTest(mode=mode):
                result, _ = self._run_logger("""
const { createRequire } = await import('node:module');
const winston = createRequire(loggerModuleUrl)('winston');
const mode = """ + json.dumps(mode) + """;
const sink = new winston.Transport({
  level: 'debug',
  log: (info, callback) => queueMicrotask(() => callback(new Error('BATCH_CALLBACK_FAULT'))),
  ...(mode === 'formatter' ? { format: winston.format(() => { throw new Error('BATCH_FORMATTER_FAULT'); })() } : {}),
});
logger.add(sink);
sink.cork();
for (let i = 0; i < 2; i++) sink.write({ level: 'debug', [Symbol.for('level')]: 'debug', message: 'fault' });
sink.uncork();
await closeLogger();
process.stdout.write('CLOSE_COMPLETED\\n');
""")
                self.assertNotEqual(result.returncode, 0, "a batch fault must fail the actual Writable stream")
                self.assertIn("BATCH_" + mode.upper() + "_FAULT", result.stderr)
                self.assertNotIn("CLOSE_COMPLETED", result.stdout)


class LoggerProvisioning(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location("logger_provisioning_test", PROVISION)
        self.provisioner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.provisioner)
        self.manifest = json.loads(self.provisioner.MANIFEST.read_text(encoding="utf-8"))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        modules = pathlib.Path(self.tmp.name) / "node_modules"
        self.home = modules / "promptfoo"
        self.home.mkdir(parents=True)
        installed = pathlib.Path(os.environ["PROMPTFOO_HOME"]).resolve()
        shutil.copy2(installed / "package.json", self.home / "package.json")
        source = next(p for p in (installed / "node_modules/winston", installed.parent / "winston")
                      if (p / "package.json").exists())
        self.dependency = modules / "winston"
        shutil.copytree(source, self.dependency)
        transport = next(p for p in (source / "node_modules/winston-transport", installed.parent / "winston-transport")
                         if (p / "package.json").exists())
        shutil.copytree(transport, modules / "winston-transport")
        self.source = self.dependency / self.manifest["source"]
        if self.provisioner.digest(self.source.read_bytes()) == self.manifest["source_sha256_after"]:
            # Derive a pristine real-source control from the checked backport.
            # Its full preimage digest must match before any test may use it.
            result = subprocess.run(
                ["patch", "--batch", "--fuzz=0", "--reverse", str(self.source)],
                input=(self.provisioner.PATCHES / self.manifest["patch"]).read_bytes(),
                capture_output=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.provisioner.digest(self.source.read_bytes()),
                         self.manifest["source_sha256_before"])

    def test_unprovisioned_check_is_readonly_and_apply_is_hash_verified(self):
        before = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "run explicitly:.*--apply"):
            self.provisioner.provision(self.home)
        self.assertEqual(self.source.read_bytes(), before)
        self.provisioner.provision(self.home, apply=True)
        patched = self.source.read_bytes()
        self.assertEqual(self.provisioner.digest(patched), self.manifest["source_sha256_after"])
        self.provisioner.provision(self.home)
        self.provisioner.provision(self.home, apply=True)
        self.assertEqual(self.source.read_bytes(), patched)

    def test_unexpected_source_is_rejected_without_mutation(self):
        transport = self.home.parent / "winston-transport/modern.js"
        for source in (self.source, transport):
            pristine = source.read_bytes()
            source.write_bytes(pristine + b"\n// altered source\n")
            before = source.read_bytes()
            for apply in (False, True):
                with self.subTest(source=source.name, apply=apply), self.assertRaisesRegex(
                    ValueError, "unexpected winston.* logger source"
                ):
                    self.provisioner.provision(self.home, apply=apply)
                self.assertEqual(source.read_bytes(), before)
            source.write_bytes(pristine)
            self.assertEqual(self.provisioner.digest(self.source.read_bytes()),
                             self.manifest["source_sha256_before"])

    def test_unexpected_dependency_version_is_rejected_without_mutation(self):
        for dependency in (self.dependency, self.home.parent / "winston-transport"):
            package_path = dependency / "package.json"
            pristine = package_path.read_bytes()
            package = json.loads(pristine)
            package["version"] = "0.0.0-unexpected"
            package_path.write_text(json.dumps(package), encoding="utf-8")
            before = self.source.read_bytes()
            with self.subTest(dependency=dependency.name), self.assertRaisesRegex(
                ValueError, "unexpected winston.* package/version"
            ):
                self.provisioner.provision(self.home, apply=True)
            self.assertEqual(self.source.read_bytes(), before)
            package_path.write_bytes(pristine)


if __name__ == "__main__":
    unittest.main()
