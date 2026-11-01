#!/usr/bin/env python3
"""Offline regression fixtures executing the calibration workflow's real steps."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import yaml

REPO = Path(__file__).resolve().parents[3]
WORKFLOW = yaml.safe_load((REPO / '.github/workflows/calibration-sheet.yml').read_text())
STEPS = {s['name']: s for s in WORKFLOW['jobs']['sheet']['steps'] if 'run' in s}


class CalibrationWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.work = self.root / 'work'
        self.work.mkdir()
        self.env = dict(os.environ, GITHUB_REPOSITORY='fixture/repo', RUN_ID='123',
                        N='20', PACKS='sample', ROOT=str(self.root / 'artifacts'),
                        RUNNER_TEMP=str(self.root), GITHUB_OUTPUT=str(self.root / 'output'),
                        GITHUB_STEP_SUMMARY=str(self.root / 'summary'))
        self.git('init')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        pack = self.work / 'plugins/sample/evals/promptfoo'
        pack.mkdir(parents=True)
        (pack / 'rubric').write_text('source rubric')
        sampler = self.work / 'evals/paid/calibration/sample-for-labelling.py'
        sampler.parent.mkdir(parents=True)
        sampler.write_text((REPO / 'evals/paid/calibration/sample-for-labelling.py').read_text())
        self.git('add', '.')
        self.git('commit', '-m', 'source')
        self.sha = self.git('rev-parse', 'HEAD').stdout.strip()
        subprocess.run(['git', 'init', '--bare', str(self.root / 'remote')], check=True, capture_output=True)
        self.git('remote', 'add', 'origin', str(self.root / 'remote'))
        self.git('push', 'origin', 'HEAD:refs/heads/main')

    def git(self, *args, check=True):
        return subprocess.run(['git', *args], cwd=self.work, text=True, capture_output=True, check=check)

    def step(self, name, ok=True, **env):
        result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', STEPS[name]['run']],
                                cwd=self.work, env=dict(self.env, **env), text=True, capture_output=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def artifact(self, pack='sample', kind='promptfoo-results', sha=None, attempt='1'):
        directory = Path(self.env['ROOT']) / pack / kind
        directory.mkdir(parents=True)
        filename = 'results.json' if kind == 'promptfoo-results' else 'results.matrix.json'
        result = directory / filename
        result.write_text(json.dumps({'results': [{'description': 'scenario', 'success': True,
                                                  'response': {'output': 'answer'}}]}))
        meta = dict(checkout_sha=sha or self.sha, repository='fixture/repo', run_id='123',
                    run_attempt=attempt, pack=pack, result=filename,
                    sha256=hashlib.sha256(result.read_bytes()).hexdigest())
        provenance = directory / 'provenance.json'
        provenance.write_text(json.dumps(meta))
        (directory.parent / 'kind').write_text(kind)
        return result, provenance

    def test_decimal_normalization_and_pack_validation(self):
        for run in ['08', '010', '99999999999999999999']:
            self.step('validate the dispatch inputs', RUN_ID=run, PACKS=' sample ,sample ')
            output = Path(self.env['GITHUB_OUTPUT']).read_text()
            self.assertIn(f'run_id={int(run)}\n', output)
            self.assertIn(f'seed={int(run) % 2147483647}\n', output)
            self.assertTrue(output.endswith('packs=sample\n'))
        for field, values in {'RUN_ID': ['0', '-1', '1\n2', 'x'], 'N': ['0', '-1', '10000'],
                              'PACKS': ['', '.', '..', '../sample', 'sam ple', 'sample,', 'sample\nother']}.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.step('validate the dispatch inputs', ok=False, **{field: value})

    def test_both_producers_emit_verifiable_provenance(self):
        for workflow, kind in [('evals.yml', 'promptfoo-results'), ('subject-matrix.yml', 'subject-matrix')]:
            result, provenance = self.artifact(kind=kind)
            provenance.unlink()
            pack = self.work / 'plugins/sample/evals/promptfoo'
            (pack / result.name).write_bytes(result.read_bytes())
            doc = yaml.safe_load((REPO / '.github/workflows' / workflow).read_text())
            steps = [s for job in doc['jobs'].values() for s in job.get('steps', [])]
            producer = next(s for s in steps if s.get('name') == 'record results checkout provenance')
            p = subprocess.run(['bash', '-e', '-c', producer['run']], cwd=pack,
                               env=dict(self.env, GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='1', PACK='sample'),
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            provenance.write_bytes((pack / 'provenance.json').read_bytes())
            self.step('verify artifact provenance')
            self.assertIn(f'sha={self.sha}', Path(self.env['GITHUB_OUTPUT']).read_text())

    def test_missing_or_tampered_provenance_rejected(self):
        result, provenance = self.artifact()
        original = provenance.read_text()
        provenance.unlink()
        self.step('verify artifact provenance', ok=False)
        for key, value in [('checkout_sha', 'bad'), ('repository', 'other/repo'), ('run_id', '124'),
                           ('pack', 'other'), ('result', 'other.json'), ('sha256', 'bad'), ('run_attempt', '0')]:
            meta = json.loads(original)
            meta[key] = value
            provenance.write_text(json.dumps(meta))
            self.step('verify artifact provenance', ok=False)
        provenance.write_text(original)
        result.write_text('{}')
        self.step('verify artifact provenance', ok=False)

    def test_ambiguous_and_symlink_artifacts_rejected(self):
        result, _ = self.artifact()
        extra = result.parent / 'results.extra.json'
        extra.write_text('{}')
        self.step('verify artifact provenance', ok=False)
        extra.unlink()
        extra.symlink_to(result)
        self.step('verify artifact provenance', ok=False)

    def test_download_fallback_uses_separate_directories(self):
        stub = self.root / 'bin'
        stub.mkdir()
        gh = stub / 'gh'
        gh.write_text("""#!/usr/bin/env python3
import pathlib, sys
args = sys.argv
name = args[args.index('-n') + 1]
dest = pathlib.Path(args[args.index('-D') + 1])
if name.startswith('subject-matrix-'):
    (dest / 'results.partial.json').write_text('{}')
    sys.exit(1)
(dest / 'results.json').write_text('{}')
""")
        gh.chmod(0o755)
        self.step('download the results artifacts', PATH=str(stub) + os.pathsep + os.environ['PATH'])
        output = Path(self.env['GITHUB_OUTPUT']).read_text()
        root = Path(next(line.split('=', 1)[1] for line in output.splitlines() if line.startswith('root=')))
        self.assertEqual((root / 'sample/kind').read_text().strip(), 'promptfoo-results')
        self.assertFalse((root / 'sample/promptfoo-results/results.partial.json').exists())

    def test_source_output_symlink_rejected(self):
        self.artifact()
        directory = self.work / 'plugins/sample/evals/promptfoo/calibration'
        directory.symlink_to(self.root, target_is_directory=True)
        self.git('add', '.')
        self.git('commit', '-m', 'symlink fixture')
        sha = self.git('rev-parse', 'HEAD').stdout.strip()
        self.step('check out the recorded source revision', ok=False, SHA=sha)

    def test_mixed_revision_or_attempt_rejected(self):
        self.artifact()
        _, provenance = self.artifact(pack='other', sha='a' * 40)
        self.step('verify artifact provenance', ok=False, PACKS='sample other')
        meta = json.loads(provenance.read_text())
        meta.update(checkout_sha=self.sha, run_attempt='2')
        provenance.write_text(json.dumps(meta))
        self.step('verify artifact provenance', ok=False, PACKS='sample other')

    def test_source_checkout_sampling_and_publish_preserve_labels(self):
        self.artifact()
        self.step('verify artifact provenance')
        # Dispatch no longer contains the historical pack.
        self.git('rm', '-r', 'plugins')
        self.git('commit', '-m', 'remove old pack')
        self.step('validate the dispatch inputs')
        self.step('check out the recorded source revision', SHA=self.sha)
        self.assertEqual(self.git('rev-parse', 'HEAD').stdout.strip(), self.sha)
        self.step('draw the blind sheets', SEED='123')
        self.step('commit the sheets to a calibration branch', SHA=self.sha)
        self.assertEqual(self.git('rev-parse', 'HEAD^').stdout.strip(), self.sha)
        sheet = self.work / 'plugins/sample/evals/promptfoo/calibration/123.sheet.json'
        rows = json.loads(sheet.read_text())
        self.assertIsNone(rows[0]['label'])
        rows[0]['label'] = 'pass'
        sheet.write_text(json.dumps(rows))
        self.git('add', '.')
        self.git('commit', '-m', 'human labels')
        self.git('push', 'origin', 'HEAD:refs/heads/calibration/123')
        labelled = self.git('rev-parse', 'HEAD').stdout.strip()
        self.step('download the results artifacts', ok=False)
        # Also exercise the race guard, bypassing the early existence check.
        self.git('checkout', '--detach', self.sha)
        self.git('branch', '-D', 'calibration/123')
        self.step('draw the blind sheets', SEED='123')
        self.step('commit the sheets to a calibration branch', ok=False, SHA=self.sha)
        self.assertEqual(self.git('ls-remote', 'origin', 'refs/heads/calibration/123').stdout.split()[0], labelled)


if __name__ == '__main__':
    unittest.main()
