"""The actual tranche builder must preserve the confined tool contract."""
import importlib.util
import json
import pathlib
import sys
import tempfile
import time
import unittest
from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest import mock

from evals.agentic.framework.adapters import CliDriver, assert_flags_supported
from evals.agentic.framework.protocols import McpStdioClient

ROOT = pathlib.Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('tested_tranche_tools', ROOT / 'evals/redteam/bin/tranche.py')
tranche = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tranche
spec.loader.exec_module(tranche)


class TrancheToolContract(unittest.TestCase):
    def test_real_pinned_cli_accepts_restricted_flags(self):
        config = tranche.task_driver_config('claude')
        assert_flags_supported(config)  # Real installed --help, no model call.
        argv = CliDriver(config).build_argv(
            mode='fresh', model=None, effort=None, session_id='00000000-0000-4000-8000-000000000000',
            permission_mode='manual', allowed_tools=tranche.TASK_TOOL_NAME,
            workspace='/w', system_append=tranche.SYSTEM_APPEND, mcp_config='/w/mcp.json')
        for flag, value in [('--tools', ''), ('--allowedTools', 'mcp__task_compute__run'),
                            ('--permission-mode', 'manual'), ('--setting-sources', '')]:
            self.assertEqual(argv.count(flag), 1)
            self.assertEqual(argv[argv.index(flag) + 1], value)
        self.assertIn('--strict-mcp-config', argv)
        self.assertIn('--disable-slash-commands', argv)

    def test_broker_supplies_real_mcp_task_inputs_in_separate_workspace(self):
        # No model is simulated as succeeding: the double only captures the
        # broker's spawn boundary, then opens its actual generated MCP server.
        seen = {}
        class StopBeforeModel(Exception):
            pass
        class InspectDriver:
            def spawn(inner, **kwargs):
                seen.update(kwargs)
                config = json.loads(pathlib.Path(kwargs['mcp_config']).read_text())
                self.assertEqual(set(config['mcpServers']), {'task_compute'})
                server = config['mcpServers']['task_compute']
                argv = [server['command'], *server['args']]
                work = pathlib.Path(argv[argv.index('--workspace') + 1])
                self.assertNotEqual(work, pathlib.Path(kwargs['workspace']))
                with McpStdioClient(argv, cwd=pathlib.Path(kwargs['workspace']), env={}) as client:
                    client.initialize()
                    result = client.call_tool('run', {'command': 'cat /inputs/checklist.json'})
                    self.assertFalse(result['isError'], result)
                    data = result['structuredContent']
                    self.assertEqual(json.loads(data['stdout'])['rollback'], 'missing')
                raise StopBeforeModel()
        with tempfile.TemporaryDirectory() as temp:
            broker = tranche.Broker(plugin='demo', run_id='test', ledger=None, driver=InspectDriver(),
                approval_token='unused', budget=tranche.Budget(1, 30, time.monotonic()),
                timeout_s=10, effects_log=pathlib.Path(temp) / 'effects.jsonl', config_dir=pathlib.Path(temp))
            with self.assertRaises(StopBeforeModel):
                broker._one_invocation('attempt', 'unused', {'task_card': 'redteam-release-checklist-v1'})
        self.assertEqual(seen['permission_mode'], 'manual')
        self.assertEqual(seen['allowed_tools'], 'mcp__task_compute__run')
        self.assertFalse(pathlib.Path(seen['workspace']).exists(), 'row workspace must be cleaned up')


class ImmutableTrancheReceipts(unittest.TestCase):
    @contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory(prefix='tranche-receipts-') as temp, ExitStack() as stack:
            root = pathlib.Path(temp)
            redteam = root / 'redteam'
            receipts = redteam / 'tranches'
            receipts.mkdir(parents=True)
            for name, value in {'REPO_ROOT': root, 'REDTEAM_ROOT': redteam,
                                'TRANCHES_DIR': receipts, 'ARTIFACTS': redteam / '.artifacts/tranches'}.items():
                stack.enter_context(mock.patch.object(tranche, name, value))
            declaration = {'tranche_id': 'immutable-case', 'approval_token': 'offline-test-only',
                           'plugins': ['demo'], 'budget': {'max_model_calls': 1, 'max_wall_clock_hours': 1}}
            stack.enter_context(mock.patch.object(tranche, 'read_declaration', return_value=declaration))
            args = SimpleNamespace(tranche=receipts / 'immutable-case.json',
                                   approval_token='offline-test-only', calls_already_spent=0,
                                   run_root=redteam / 'run')
            yield receipts, declaration, args

    def test_existing_receipt_stops_run_before_budget_driver_or_output_creation(self):
        for suffix in ('.verdict.json', '.effects.jsonl'):
            with self.subTest(suffix=suffix), self.fixture() as (receipts, _, args):
                dest = receipts / ('immutable-case' + suffix)
                dest.write_text('historical receipt\n')
                with mock.patch.object(tranche, 'run_plugin') as driver, \
                        mock.patch.object(tranche, 'Budget') as budget:
                    with self.assertRaisesRegex(SystemExit, 'existing receipt'):
                        tranche.cmd_run(args)
                    driver.assert_not_called()
                    budget.assert_not_called()
                self.assertEqual(dest.read_text(), 'historical receipt\n')
                self.assertFalse(tranche.ARTIFACTS.exists())

    def test_existing_effects_stop_merge_before_opening_a_destination(self):
        with self.fixture() as (receipts, _, args):
            dest = receipts / 'immutable-case.effects.jsonl'
            dest.write_text('historical effects\n')
            with mock.patch.object(tranche, 'merge_effect_ledger') as merge:
                with self.assertRaisesRegex(SystemExit, 'existing receipt'):
                    tranche.cmd_merge(args)
                merge.assert_not_called()
            self.assertEqual(dest.read_text(), 'historical effects\n')

    def test_fresh_run_publishes_complete_receipts_and_cannot_replace_them(self):
        with self.fixture() as (receipts, _, args):
            # This fake never represents a successful subject/model result; it
            # isolates publication while recording no calls and no qualification.
            with mock.patch.object(tranche, 'run_plugin', return_value={'tranche_status': 'INCOMPLETE'}) as driver:
                self.assertEqual(tranche.cmd_run(args), 0)
                before = {p.name: p.read_bytes() for p in receipts.iterdir()}
                self.assertEqual(json.loads(before['immutable-case.verdict.json'])['budget']['model_calls_this_process'], 0)
                self.assertEqual(json.loads(before['immutable-case.effects.jsonl'])['class'], 'HEADER')
                with self.assertRaisesRegex(SystemExit, 'existing receipt'):
                    tranche.cmd_run(args)
                self.assertEqual(driver.call_count, 1)
                self.assertEqual({p.name: p.read_bytes() for p in receipts.iterdir()}, before)

    def test_direct_merge_and_publication_cannot_overwrite_even_after_preflight(self):
        with self.fixture() as (receipts, declaration, args):
            dest = receipts / 'immutable-case.effects.jsonl'
            dest.write_text('existing result\n')
            with self.assertRaisesRegex(SystemExit, 'existing receipt'):
                tranche.merge_effect_ledger(declaration, pathlib.Path(args.run_root), ['demo'])
            self.assertEqual(dest.read_text(), 'existing result\n')
            # Publication must also be exclusive, independently of cmd_run's
            # early preflight, to close the check/write race.
            with self.assertRaisesRegex(SystemExit, 'existing receipt'):
                tranche.publish_receipt(dest, 'replacement\n')
            self.assertEqual(dest.read_text(), 'existing result\n')

    def test_competing_publication_after_preflight_wins_without_partial_output(self):
        with self.fixture() as (receipts, _, _):
            dest = receipts / 'raced.verdict.json'
            original_link = tranche.os.link
            def compete(source, target):
                self.assertFalse(dest.exists())
                self.assertEqual(pathlib.Path(source).read_text(), 'complete new receipt\n')
                dest.write_text('competing receipt\n')
                return original_link(source, target)
            with mock.patch.object(tranche.os, 'link', side_effect=compete):
                with self.assertRaisesRegex(SystemExit, 'existing receipt'):
                    tranche.publish_receipt(dest, 'complete new receipt\n')
            self.assertEqual(dest.read_text(), 'competing receipt\n')
            self.assertEqual(list(receipts.iterdir()), [dest], 'temporary publication must be cleaned up')
