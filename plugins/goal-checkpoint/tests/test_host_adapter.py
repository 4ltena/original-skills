import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

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


if __name__ == '__main__':
    unittest.main()
