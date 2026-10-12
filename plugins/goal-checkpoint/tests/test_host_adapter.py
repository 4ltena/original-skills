import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import concurrent.futures
from unittest.mock import patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import host_adapter as adapter


class HostAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.data = self.base / 'data'; self.data.mkdir(mode=0o700)
        self.workspace = self.base / 'workspace'; self.workspace.mkdir()
        self.details = {'goal_status': 'active', 'budget_exhausted': False,
            'goal_ref': 'manual-monitor', 'milestone': 'M1', 'criteria': 'approved criterion', 'evidence': 'unknown'}

    def tearDown(self):
        self.temp.cleanup()

    def operation(self, name, details=None, session='session-a', now=10):
        return adapter.operate(str(self.data), 'claude', name, session, str(self.workspace), details or {}, now)

    def event(self, name, now=10, **extra):
        return adapter.claude_hook(str(self.data), {'hook_event_name': name, 'session_id': 'session-a',
            'cwd': str(self.workspace), **extra}, now)

    def test_full_claude_lifecycle_and_stop_deduplication(self):
        state = self.operation('enable', self.details)
        self.assertEqual(self.event('UserPromptSubmit'), {})
        self.assertEqual(self.event('PostToolUse', 100), {})
        output = self.event('PostToolUse', 10811)
        self.assertIn('additionalContext', output['hookSpecificOutput'])
        self.assertIn('明示した目的', output['hookSpecificOutput']['additionalContext'])
        blocked = self.event('Stop', 10812)
        self.assertEqual(blocked['decision'], 'block')
        self.assertEqual(self.event('Stop', 10813, stop_hook_active=True), {})
        reviewed = self.operation('review', now=10813)
        ack = {**self.details, 'generation': state['generation'], 'checkpoint_id': reviewed['pending']['id'], 'verdict': 'progress'}
        self.assertIsNone(self.operation('ack', ack, now=10814)['pending'])
        self.operation('disable', {'reason': 'user stopped'}, now=10815)
        self.assertEqual(self.event('UserPromptSubmit', 25000), {})
        self.assertEqual(self.event('Stop', 25001), {})

    def test_session_separation_unknown_objective_and_no_native_goal_inference(self):
        self.assertFalse(self.operation('status')['registered'])
        self.event('UserPromptSubmit')
        self.event('PostToolUse', tool_name='create_goal', tool_response={'goal': {'status': 'active'}}, tool_use_id='id')
        self.assertFalse(self.operation('status')['registered'])
        self.operation('enable', self.details)
        self.assertFalse(self.operation('status', session='session-b')['registered'])
        with self.assertRaises(adapter.core.StateError):
            self.operation('enable', {**self.details, 'goal_status': 'paused'}, session='session-b')
        self.assertEqual(self.event('SessionEnd', 25000), {})
        self.assertEqual(self.event('Interrupt', 25000), {})

    def test_compact_and_resume_recover_pending_context_without_turn_dedup(self):
        self.operation('enable', self.details)
        self.event('UserPromptSubmit')
        self.event('PostToolUse', 10811)
        compact = self.event('SessionStart', 10812, source='compact')
        self.assertIn('additionalContext', compact['hookSpecificOutput'])
        self.assertEqual(self.event('SessionStart', 10813, source='compact'), {})
        resumed = self.event('SessionStart', 10814, source='resume')
        self.assertIn('additionalContext', resumed['hookSpecificOutput'])

    def receipt(self):
        return json.loads((self.data / 'goal-checkpoint' / 'hook-observations.json').read_text())

    def test_observation_receipt_is_bounded_content_free_and_unknown_events_do_not_write(self):
        secret = 'prompt/session/cwd must not persist'
        self.assertEqual(self.event('UnknownEvent', payload=secret), {})
        self.assertFalse((self.data / 'goal-checkpoint').exists())
        for index in range(34):
            self.event('SessionEnd', now=100 + index, payload=secret, cwd=secret)
        receipt = self.receipt()
        self.assertEqual(receipt['version'], 1)
        self.assertEqual(len(receipt['observations']), 32)
        self.assertTrue(all(set(item) == {'event', 'at', 'elapsed_ms', 'outcome'} for item in receipt['observations']))
        self.assertNotIn(secret, json.dumps(receipt))
        self.assertLessEqual(len(json.dumps(receipt).encode()), adapter.core.MAX_STATE)

    def test_claude_unsupported_interrupt_has_no_state_or_observation(self):
        self.assertEqual(self.event('Interrupt'), {})
        self.assertFalse((self.data / 'goal-checkpoint').exists())

    def test_claude_session_end_records_without_session_or_core_state(self):
        self.assertEqual(adapter.claude_hook(str(self.data), {'hook_event_name': 'SessionEnd'}, 10), {})
        receipt = self.receipt()
        self.assertEqual(receipt['observations'][-1]['event'], 'SessionEnd')
        self.assertEqual(list((self.data / 'goal-checkpoint').glob('*.index.json')), [])

    def test_observation_normalizes_corrupted_extra_fields(self):
        secret = 'cwd/session/prompt must be removed'
        with adapter.core.Store(str(self.data)) as store:
            store.write('hook-observations.json', {
                'version': 1, 'payload': secret,
                'observations': [{'event': 'SessionStart', 'at': 1, 'elapsed_ms': 2, 'outcome': 'ok', 'cwd': secret}],
            })
        self.assertEqual(adapter.claude_hook(str(self.data), {'hook_event_name': 'SessionEnd'}, 10), {})
        receipt = self.receipt()
        self.assertEqual(set(receipt), {'version', 'observations'})
        self.assertTrue(all(set(item) == {'event', 'at', 'elapsed_ms', 'outcome'} for item in receipt['observations']))
        self.assertNotIn(secret, json.dumps(receipt))

    def test_observation_failure_does_not_change_hook_result(self):
        with patch.object(adapter.core.Store, 'write', side_effect=PermissionError('denied')):
            self.assertEqual(self.event('SessionEnd'), {})
        self.assertFalse((self.data / 'goal-checkpoint' / 'hook-observations.json').exists())

    def test_observation_records_known_hook_errors(self):
        with self.assertRaises(adapter.core.StateError):
            adapter.claude_hook(str(self.data), {'hook_event_name': 'Stop', 'session_id': ''}, 10)
        receipt = self.receipt()
        self.assertEqual(receipt['observations'][-1]['event'], 'Stop')
        self.assertEqual(receipt['observations'][-1]['outcome'], 'error')

    def test_observation_fixed_lock_preserves_two_sessions(self):
        events = [
            {'hook_event_name': 'SessionEnd', 'session_id': 'session-a', 'cwd': str(self.workspace)},
            {'hook_event_name': 'SessionEnd', 'session_id': 'session-b', 'cwd': str(self.workspace)},
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outputs = list(pool.map(lambda event: adapter.claude_hook(str(self.data), event, 10), events))
        self.assertEqual(outputs, [{}, {}])
        self.assertEqual(len(self.receipt()['observations']), 2)


if __name__ == '__main__':
    unittest.main()
