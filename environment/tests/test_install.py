import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ENV = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENV))
import install
import runtime
sys.path.insert(0, str(ENV / 'scripts'))
import git_guard


def answers(host='claude', **override):
    value = {'host': host, 'scope': 'user', 'skills': 'basic', 'plugins': [],
             'git_mode': 'manual-git', 'settings': 'candidates'}
    if host != 'codex':
        value['surface'] = 'cli'
    value = {**value, **override}
    if 'growth-loop' in value['plugins']:
        value['growth_root'] = 'selected-skills'
    return value


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name).resolve()

    def tearDown(self):
        self.temp.cleanup()

    def test_question_sequence_branching_edit_cancel_and_invalid_answers(self):
        value = {}
        for key in ('host', 'surface', 'scope', 'skills', 'plugins', 'git_mode', 'settings'):
            self.assertEqual(install.questions(value)['id'], key)
            value[key] = answers()[key]
        self.assertIsNone(install.questions(value))
        self.assertEqual(list(self.home.iterdir()), [])  # Questions/cancel have no side effects.
        value.pop('skills')
        self.assertEqual(install.questions(value)['id'], 'skills')
        with self.assertRaises(ValueError):
            install.plan(answers(git_mode='surprise'), self.home)
        self.assertEqual(list(self.home.iterdir()), [])
        with self.assertRaises(ValueError):
            install.plan(answers(host='codex', surface='cli'), self.home)
        growth = answers(plugins=['growth-loop'], auto_delete='yes')
        growth.pop('growth_root')
        question = install.questions(growth, self.home)
        self.assertEqual(question['id'], 'growth_root')
        self.assertEqual(question['paths']['claude'], str(self.home / '.claude/skills'))
        with self.assertRaises(ValueError):
            install.plan(growth, self.home)

    def test_clis_absent_plan_apply_preserves_existing_frontend_and_settings(self):
        folder = self.home / '.claude/skills/frontend-design'; folder.mkdir(parents=True)
        original = folder / 'SKILL.md'; original.write_text('my frontend')
        with patch.object(subprocess, 'run', wraps=subprocess.run) as run:
            result = install.plan(answers(skills='all', plugins=['workflow', 'growth-loop', 'goal-checkpoint'],
                auto_delete='yes', checkpoint='enabled'), self.home)
            # The only external process is the explicit Python probe; no agent CLI.
            self.assertTrue(all(Path(call.args[0][0]).resolve() == Path(sys.executable).resolve() for call in run.call_args_list))
        self.assertEqual(len(result['selected_skills']), 46)
        self.assertIn(str(folder), result['preserved'])
        self.assertFalse((self.home / '.claude/settings.json').exists())
        applied = install.apply(result, result['plan_id'])
        self.assertFalse(applied['runtime_verified'])
        self.assertEqual(original.read_text(), 'my frontend')
        self.assertFalse((self.home / '.claude/settings.json').exists())
        candidate = json.loads((self.home / '.claude/original-skills-settings.candidate.json').read_text())
        self.assertEqual(candidate['enabledPlugins'], {})
        self.assertEqual(candidate['extraKnownMarketplaces'], {})
        self.assertNotIn('Interrupt', candidate['hooks'])
        for entries in candidate['hooks'].values():
            for entry in entries:
                for hook in entry['hooks']:
                    self.assertEqual(hook['command'], sys.executable)
                    self.assertEqual(hook['args'][:3], ['-X', 'utf8', '-B'])
        skill = (self.home / '.claude/skills/forget/SKILL.md').read_text()
        self.assertIn('allowed-tools:', skill)
        self.assertIn(str(self.home / '.claude/original-skills/growth-loop/bin/gl-run'), skill)

    def test_all_skills_metadata_and_local_reference_resolution(self):
        result = install.plan(answers(skills='all', plugins=['workflow','growth-loop','goal-checkpoint'],
            auto_delete='yes', checkpoint='enabled'), self.home)
        install.apply(result, result['plan_id'])
        root = self.home / '.claude/skills'
        matrix = json.loads((ENV / 'skill-compatibility.json').read_text())['skills']
        self.assertEqual(set(matrix), set(install.inventory()))
        self.assertEqual(set(matrix), {p.name for p in root.iterdir()})
        for name in matrix:
            with self.subTest(name=name):
                document = root / name / 'SKILL.md'
                body = document.read_text()
                self.assertRegex(body, r'(?m)^name:\s*["\']?' + re.escape(name))
                self.assertRegex(body, r'(?m)^description:\s*\S')
                self.assertNotEqual(matrix[name]['classification'], 'blocked')
                for link in re.findall(r'\]\(([^)]+)\)', body):
                    if re.match(r'^[a-z]+:', link) or link.startswith('#'):
                        continue
                    target = Path(link.split('#')[0])
                    self.assertTrue((target if target.is_absolute() else document.parent / target).exists(), (name, link))

    def test_changed_plan_destinations_and_machine_refuse_before_any_write(self):
        result = install.plan(answers(), self.home)
        target = self.home / '.claude/skills/workflow'; target.mkdir(parents=True)
        (target / 'SKILL.md').write_text('concurrent user skill')
        with self.assertRaises(ValueError):
            install.apply(result, result['plan_id'])
        self.assertFalse((self.home / '.claude/original-skills').exists())
        with self.assertRaises(ValueError):
            install.apply(result, 'old-approval')
        fresh = install.plan(answers(), self.home)
        fresh['home'] = str(self.home / 'another-machine')
        with self.assertRaises(ValueError):
            install.apply(fresh, fresh['plan_id'])
        fresh = install.plan(answers(), self.home)
        with patch.object(install.platform, 'node', return_value='other-host'):
            with self.assertRaises(ValueError):
                install.apply(fresh, fresh['plan_id'])

    def test_settings_merge_only_selected_and_backup(self):
        root = self.home / '.claude'; root.mkdir()
        settings = root / 'settings.json'
        original = {'model': 'chosen', 'enabledPlugins': {'user-design@personal': True}, 'permissions': {'ask': ['Bash(custom *)']}}
        settings.write_text(json.dumps(original))
        result = install.plan(answers(settings='apply-selected'), self.home)
        applied = install.apply(result, result['plan_id'])
        current = json.loads(settings.read_text())
        self.assertEqual(current['model'], 'chosen')
        self.assertEqual(current['enabledPlugins'], original['enabledPlugins'])
        backup = next(item['backup'] for item in applied['written'] if item['path'] == str(settings))
        self.assertEqual(json.loads(Path(backup).read_text()), original)
        self.assertIn('Bash(git commit*)', current['permissions']['ask'])
        self.assertNotIn('~/.codex', (root / 'CLAUDE.md').read_text())

    def test_selected_only_chat_no_hooks_and_codex_manual_rules(self):
        result = install.plan(answers(surface='chat', skills='custom', skill_names=['code-inspection']), self.home)
        install.apply(result, result['plan_id'])
        self.assertEqual([p.name for p in (self.home / '.claude/skills').iterdir()], ['code-inspection'])
        candidate = json.loads((self.home / '.claude/original-skills-settings.candidate.json').read_text())
        self.assertEqual(candidate['hooks'], {})
        result = install.plan(answers(host='codex', settings='apply-selected'), self.home)
        install.apply(result, result['plan_id'])
        rules = (self.home / '.codex/rules/original-skills-manual-git.rules').read_text()
        self.assertIn('["git", "commit"]', rules)
        self.assertFalse((self.home / '.codex/config.toml').exists())

    def test_invalid_probe_and_shell_paths(self):
        for executable in ('C:/Users/Test/AppData/Local/Microsoft/WindowsApps/python3.exe', str(self.home / 'missing-python')):
            with self.assertRaises((ValueError, OSError)):
                runtime.probe(executable)
        with self.assertRaises(ValueError):
            runtime.probe('/usr/bin/python3') if sys.platform == 'darwin' else runtime.command(['bad\npath'])
        for char in ('%', '!', '&', '"', '\n', '\0'):
            with self.assertRaises(ValueError):
                runtime.command(['C:/Python' + char + '/python.exe'], 'win32')
        words = ['/real path/日本語/python', 'script with $ ` and quote\' .py']
        self.assertEqual(shlex.split(runtime.command(words, 'darwin')), words)
        self.assertEqual(runtime.command(['C:/Program Files/Python/python.exe', '日本語.py'], 'win32'),
                         '"C:/Program Files/Python/python.exe" "日本語.py"')

    def test_manual_guard_git_order_compound_gh_wrappers_and_owned_helper(self):
        for command in ('git add a', 'git commit -m x', 'git -C repo push origin feat',
                        'git merge feat', 'git tag v1', 'gh pr create', 'gh pr edit 1', 'gh api repos/x',
                        'echo ok && git push', 'git status; git commit', 'python wrapper.py', 'git -c alias.x=push x'):
            self.assertEqual(git_guard.decision(command), 'ask', command)
        self.assertEqual(git_guard.decision('git status && gh pr list'), 'allow')
        self.assertEqual(git_guard.decision('git push --delete origin old'), 'deny')
        self.assertEqual(git_guard.decision('gh repo delete owner/repo'), 'deny')
        helper = '/managed/bin/gl-run'; python = '/verified/python'
        command = runtime.command([python, '-X', 'utf8', '-B', helper, 'owned', 'delete', 'demo', '--generation', 'a' * 32, '--reason', 'obsolete'])
        self.assertEqual(git_guard.decision(command, helper, python), 'allow')
        self.assertEqual(git_guard.decision(command + ' --binding /tmp/forged', helper, python), 'deny')
        automatic = install.settings_for('claude', answers(git_mode='automatic'), Path('/safe'), runtime.probe(), {})
        self.assertFalse(automatic['hooks'])


if __name__ == '__main__':
    unittest.main()
