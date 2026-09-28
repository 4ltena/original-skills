from __future__ import annotations

import contextlib
import importlib.machinery
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "git-read"
LOADER = importlib.machinery.SourceFileLoader("git_read", str(SCRIPT))
SPEC = importlib.util.spec_from_loader("git_read", LOADER)
assert SPEC and SPEC.loader
git_read = importlib.util.module_from_spec(SPEC)
sys.modules["git_read"] = git_read
SPEC.loader.exec_module(git_read)


class GitReadTests(unittest.TestCase):
    def test_real_fixture_reads_preserve_repository_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repo"
            subprocess.run([git_read.GIT, "init", "-q", str(repository)], check=True)
            tracked = repository / "tracked.txt"
            tracked.write_text("fixture\n", encoding="utf-8")
            subprocess.run([git_read.GIT, "-C", str(repository), "add", "tracked.txt"], check=True)
            subprocess.run([git_read.GIT, "-C", str(repository), "commit", "-q", "-m", "test fixture"], check=True)

            def snapshot() -> tuple[bytes, bytes, bytes, bytes, str]:
                refs = subprocess.run(
                    [git_read.GIT, "-C", str(repository), "show-ref"], check=True,
                    capture_output=True,
                ).stdout
                status = subprocess.run(
                    [git_read.GIT, "-C", str(repository), "status", "--porcelain=v1"], check=True,
                    capture_output=True, text=True,
                ).stdout
                return (
                    tracked.read_bytes(), (repository / ".git" / "index").read_bytes(), refs,
                    (repository / ".git" / "config").read_bytes(), status,
                )

            before = snapshot()
            original = Path.cwd()
            try:
                os.chdir(repository)
                for argv in (
                    ["status", "--short"], ["log", "-n", "1", "--oneline"],
                    ["show", "HEAD", "--stat"], ["diff", "--stat"], ["ls-files"],
                    ["cat-file", "-t", "HEAD"],
                ):
                    self.assertEqual(git_read.run(argv), 0, argv)
            finally:
                os.chdir(original)
            self.assertEqual(snapshot(), before)

    def test_all_allowed_families_have_a_valid_form(self) -> None:
        cases = [
            ["diff"], ["log"], ["show"], ["blame", "README.md"], ["grep", "needle"],
            ["shortlog"], ["whatchanged"], ["status"], ["rev-parse", "HEAD"],
            ["ls-files"], ["ls-tree", "HEAD"], ["for-each-ref"], ["show-ref"],
            ["merge-base", "HEAD", "main"], ["name-rev", "HEAD"], ["rev-list", "HEAD"],
            ["describe"], ["cherry", "main"], ["count-objects"],
            ["check-attr", "diff", "README.md"], ["check-ignore", "README.md"],
            ["check-mailmap", "A <a@example.test>"], ["check-ref-format", "refs/heads/x"],
            ["version"], ["cat-file", "-t", "HEAD"], ["branch", "--show-current"],
            ["remote", "get-url", "origin"], ["worktree", "list"],
            ["submodule", "status"], ["notes", "list"], ["reflog", "show"], ["tag", "--list"],
            ["config", "--get", "core.bare"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                command, _ = git_read.build_command(argv)
                self.assertEqual(command[0], git_read.GIT)

    def test_mutations_global_options_and_unknown_options_are_denied(self) -> None:
        for argv in (
            ["checkout", "main"], ["reset", "--hard"], ["-C", "/tmp", "status"],
            ["diff", "--output", "x"], ["log", "--ext-diff"], ["grep", "--textconv", "x"],
            ["show", "--unknown"], ["cat-file", "--batch"], ["worktree", "add", "x"],
        ):
            with self.subTest(argv=argv), self.assertRaises(git_read.GitReadError):
                git_read.validate(argv)

    def test_secret_config_and_arbitrary_keys_are_denied(self) -> None:
        for key in (
            "http.https://github.com/.extraheader", "credential.helper", "remote.origin.url",
            "core.pager",
        ):
            with self.subTest(key=key), self.assertRaises(git_read.GitReadError):
                git_read.validate(["config", "--get", key])
        command, _ = git_read.build_command(["config", "--get", "core.repositoryformatversion"])
        self.assertIn("--no-includes", command)

    def test_signature_formats_and_nul_are_denied(self) -> None:
        for argv in (["log", "--format=%G?"], ["for-each-ref", "--format=%(signature:grade)"], ["show", "bad\0value"]):
            with self.subTest(argv=argv), self.assertRaises(git_read.GitReadError):
                git_read.validate(argv)

    def test_paths_starting_with_dash_require_separator(self) -> None:
        with self.assertRaises(git_read.GitReadError):
            git_read.validate(["diff", "-secret"])
        git_read.validate(["diff", "--", "-secret"])

    def test_remote_http_userinfo_is_redacted(self) -> None:
        version = SimpleNamespace(returncode=0, stdout="git version 2.52.0\n", stderr="")
        remote = SimpleNamespace(returncode=0, stdout="https://user:token@example.test/o/r.git\n", stderr="")
        output = io.StringIO()
        with mock.patch.object(git_read.subprocess, "run", side_effect=[version, remote]) as run, contextlib.redirect_stdout(output):
            self.assertEqual(git_read.run(["remote", "get-url", "origin"]), 0)
        self.assertEqual(output.getvalue(), "https://[redacted]@example.test/o/r.git\n")
        self.assertFalse(run.call_args_list[1].kwargs.get("shell", False))

    def test_environment_sanitization(self) -> None:
        env = git_read.sanitized_env({
            "HOME": "/tmp/home", "GIT_DIR": "/secret", "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "credential.helper", "GIT_CONFIG_VALUE_0": "bad",
            "GIT_SSH_COMMAND": "bad", "GIT_EDITOR": "bad", "PAGER": "less",
        })
        for key in ("GIT_DIR", "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0", "GIT_SSH_COMMAND", "GIT_EDITOR"):
            self.assertNotIn(key, env)
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(env["GIT_OPTIONAL_LOCKS"], "0")
        self.assertEqual(env["GIT_PAGER"], "cat")
        self.assertEqual(env["PATH"], "/usr/bin:/bin:/usr/sbin:/sbin")

    def test_timeout_and_version_drift(self) -> None:
        version = SimpleNamespace(returncode=0, stdout="git version 2.52.0\n", stderr="")
        with mock.patch.object(git_read.subprocess, "run", side_effect=[version, subprocess.TimeoutExpired([git_read.GIT], 120)]):
            self.assertEqual(git_read.run(["status"]), git_read.EXIT_TIMEOUT)
        wrong = SimpleNamespace(returncode=0, stdout="git version 2.51.0\n", stderr="")
        with mock.patch.object(git_read.subprocess, "run", return_value=wrong):
            with self.assertRaises(git_read.GitReadError):
                git_read.run(["status"])


if __name__ == "__main__":
    unittest.main()
