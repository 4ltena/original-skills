"""Representative installed Claude entrypoints. No model runs, remote writes or real broker."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import install
from test_install import answers


class PortabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name).resolve()
        value = answers(skills='all', plugins=['workflow', 'growth-loop', 'goal-checkpoint'],
                        auto_delete='yes', checkpoint='enabled')
        result = install.plan(value, self.home)
        install.apply(result, result['plan_id'])
        self.root = self.home / '.claude'
        self.runtime = self.root / 'original-skills'

    def tearDown(self):
        self.temp.cleanup()

    def call(self, script, *args, payload=None, env=None):
        return subprocess.run([sys.executable, '-X', 'utf8', '-B', str(script), *args],
            input=json.dumps(payload) if payload is not None else None,
            text=True, encoding='utf-8', capture_output=True, timeout=10,
            env={**os.environ, **(env or {})})

    def growth(self, *args, payload=None, env=None):
        result = self.call(self.runtime / 'growth-loop/bin/gl-run', *args, payload=payload, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_learn_refine_forget_journey_profile_jot_recall(self):
        body = '---\nname: retained-route\ndescription: Use when the specific old command fails.\n---\nverified route'
        payload = {'SKILL.md': body, 'scripts/check.txt': 'support'}
        created = json.loads(self.growth('owned', 'create', 'retained-route', payload=payload))
        generation = created['generation']
        self.assertIn('retained-route', self.growth('journey'))
        self.growth('owned', 'update', 'retained-route', '--generation', generation,
                    payload={**payload, 'SKILL.md': body + '\ncorrected flag'})
        self.assertIn('corrected flag', (self.root / 'skills/retained-route/SKILL.md').read_text())
        paths = self.growth('journey', '--paths')
        self.assertIn(str(self.root / 'skills'), paths)
        # Jot/profile are portable scoped text edits at the tool-resolved paths.
        data = self.root / 'original-skills-data/growth-loop'
        (data / 'candidates.md').write_text('## one\nA specific reproducible failed flag.\n')
        (data / 'profile.md').write_text('## Preferences\n- Uses Japanese for replies (explicitly supplied).\n')
        self.assertIn('profile.md', self.growth('journey'))
        transcripts = self.home / 'transcripts'; transcripts.mkdir()
        (transcripts / 'session.jsonl').write_text(json.dumps({'type':'user','message':{'role':'user','content':[{'type':'text','text':'retained route transcript'}]}}) + '\n')
        recalled = self.growth('recall', 'retained route', env={'CLAUDE_TRANSCRIPT_DIR':str(transcripts)})
        self.assertIn('retained route', recalled)
        self.growth('owned', 'delete', 'retained-route', '--generation', generation, '--reason', 'obsolete')
        self.assertFalse((self.root / 'skills/retained-route').exists())
        self.assertTrue((data / 'profile.md').exists())
        manual = self.root / 'skills/my-manual'; manual.mkdir()
        (manual / 'SKILL.md').write_text('manual')
        refused = self.call(self.runtime / 'growth-loop/bin/gl-run', 'owned', 'delete', 'my-manual', '--generation', generation, '--reason', 'obsolete')
        self.assertNotEqual(refused.returncode, 0)
        self.assertEqual((manual / 'SKILL.md').read_text(), 'manual')

    def test_agent_watchdog_without_either_cli(self):
        script = self.root / 'skills/agent-watchdog/scripts/recovery.py'
        value = {'attempts':1,'failure_kind':'unknown','repeatable':True,'user_stopped':False,'uncertain_effects':False}
        result = self.call(script, payload=value)
        self.assertEqual(json.loads(result.stdout)['action'], 'resume-missing-work')
        for change in ({'attempts':2}, {'failure_kind':'deterministic'}, {'user_stopped':True}, {'uncertain_effects':True}):
            result = self.call(script, payload={**value, **change})
            self.assertEqual(json.loads(result.stdout)['action'], 'stop')

    def test_site_catalog_explicit_claude_root(self):
        catalog = self.root / 'site-catalog'; entries = catalog / 'entries'; entries.mkdir(parents=True)
        (entries / 'example.json').write_text(json.dumps({'schema_version':1,'id':'example','service':'Example',
            'domains':['example.test'],'accounts':[{'id':'user','username':'public-fixture'}],'license_notations':[]}))
        script = self.root / 'skills/site-account-catalog/scripts/accountctl.py'
        found = self.call(script, '--catalog', str(catalog), 'find', 'example.test')
        self.assertEqual(found.returncode, 0, found.stderr)
        self.assertEqual(json.loads(found.stdout)['status'], 'found')
        identity = self.call(script, '--catalog', str(catalog), 'identity', 'user', 'username', '--site', 'example')
        self.assertEqual(json.loads(identity.stdout)['value'], 'public-fixture')

    def test_git_and_github_read_adapters_parse_without_cli_or_network(self):
        for skill, reader, allowed, denied in (
            ('git-read-inspection','git-read',['status','--short'],['push','origin','main']),
            ('gh-read-inspection','gh-read',['pr','list'],['pr','create'])):
            namespace = runpy.run_path(str(self.root / 'skills' / skill / 'scripts' / reader))
            self.assertTrue(namespace['validate'](allowed))
            with self.assertRaises(ValueError):
                namespace['validate'](denied)
        # Git/GitHub write and release Skills route through the installed policy;
        # this guard fixture covers their operation families without performing writes.
        script = self.runtime / 'git_guard.py'
        for command in ('git commit -m demo', 'gh pr create', 'gh release create v1'):
            result = self.call(script, payload={'tool_input':{'command':command}})
            self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['permissionDecision'], 'ask')
        policy = (self.runtime / 'host-policy.md').read_text()
        self.assertIn('Do not stage, commit, push', policy)

    def test_goal_checkpoint_installed_claude_cli_and_hook(self):
        script = self.runtime / 'goal-checkpoint/scripts/host_adapter.py'
        details = {'goal_status':'active','budget_exhausted':False,'goal_ref':'explicit-purpose',
            'milestone':'M1','criteria':'approved acceptance','evidence':'unknown'}
        enabled = self.call(script, 'enable', '--host', 'claude', '--session', 'confirmed-id', '--workspace', str(self.home), payload=details)
        self.assertEqual(enabled.returncode, 0, enabled.stderr)
        state = json.loads(enabled.stdout)
        reviewed = self.call(script, 'review', '--host', 'claude', '--session', 'confirmed-id')
        pending = json.loads(reviewed.stdout)['pending']['id']
        ack = {**details,'generation':state['generation'],'checkpoint_id':pending,'verdict':'stalled'}
        acknowledged = self.call(script, 'ack', '--host', 'claude', '--session', 'confirmed-id', payload=ack)
        self.assertIsNone(json.loads(acknowledged.stdout)['pending'])
        event = {'hook_event_name':'UserPromptSubmit','session_id':'confirmed-id','cwd':str(self.home)}
        result = self.call(script, 'hook', '--host', 'claude', payload=event)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})


if __name__ == '__main__':
    unittest.main()
