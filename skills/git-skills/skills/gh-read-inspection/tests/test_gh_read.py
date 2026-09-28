from __future__ import annotations

import importlib.machinery
import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "gh-read"
LOADER = importlib.machinery.SourceFileLoader("gh_read", str(SCRIPT))
SPEC = importlib.util.spec_from_loader("gh_read", LOADER)
assert SPEC and SPEC.loader
gh_read = importlib.util.module_from_spec(SPEC)
sys.modules["gh_read"] = gh_read
SPEC.loader.exec_module(gh_read)


class GhReadTests(unittest.TestCase):
    def test_every_allowed_command_path(self) -> None:
        cases = [
            ["repo", "view"], ["repo", "list"], ["pr", "view"], ["pr", "list"],
            ["pr", "status"], ["pr", "checks"], ["pr", "diff"], ["issue", "view"],
            ["issue", "list"], ["issue", "status"], ["run", "view"], ["run", "list"],
            ["workflow", "view"], ["workflow", "list"], ["release", "view"], ["release", "list"],
            ["search", "code", "needle"], ["search", "commits", "needle"],
            ["search", "issues", "needle"], ["search", "prs", "needle"],
            ["search", "repos", "needle"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                self.assertEqual(gh_read.validate(argv), [gh_read.GH, *argv])

    def test_json_formatting_and_repo_selector_are_accepted(self) -> None:
        argv = ["pr", "view", "42", "--repo", "owner/repo", "--json", "number,title", "--jq", ".number"]
        self.assertEqual(gh_read.validate(argv), [gh_read.GH, *argv])

    def test_web_watch_output_mutations_and_unknown_options_are_denied(self) -> None:
        cases = [
            ["pr", "view", "42", "--web"], ["pr", "checks", "42", "--watch"],
            ["release", "view", "v1", "--output", "x"], ["repo", "delete", "o/r"],
            ["api", "repos/o/r"], ["auth", "status"], ["pr", "view", "--unknown"],
            ["pr", "list", "extra"], ["search", "repos", "one", "two"], ["repo", "view", "--", "--web"],
            ["repo", "view", "--repo", "evil.example/o/r"], ["repo", "view", "https://evil.example/o/r"],
        ]
        for argv in cases:
            with self.subTest(argv=argv), self.assertRaises(gh_read.GhReadError):
                gh_read.validate(argv)

    def test_environment_sanitization_preserves_auth_without_printing_it(self) -> None:
        env = gh_read.sanitized_env({
            "GH_TOKEN": "secret", "GH_BROWSER": "bad", "BROWSER": "bad", "GH_EDITOR": "bad",
            "GIT_EDITOR": "bad", "VISUAL": "bad", "EDITOR": "bad", "GH_PAGER": "less", "PAGER": "less",
        })
        self.assertEqual(env["GH_TOKEN"], "secret")
        self.assertNotIn("GH_HOST", gh_read.sanitized_env({"GH_HOST": "evil.example"}))
        for key in ("GH_BROWSER", "BROWSER", "GH_EDITOR", "GIT_EDITOR", "VISUAL", "EDITOR"):
            self.assertNotIn(key, env)
        self.assertEqual(env["GH_PAGER"], "cat")
        self.assertEqual(env["GH_PROMPT_DISABLED"], "1")

    def test_run_uses_no_shell_and_reports_timeout(self) -> None:
        version = SimpleNamespace(returncode=0, stdout="gh version 2.101.0 (2026-09-15)\n", stderr="")
        with mock.patch.object(gh_read.subprocess, "run", side_effect=[version, subprocess.TimeoutExpired([gh_read.GH], 120)]) as run:
            self.assertEqual(gh_read.run(["repo", "view"]), gh_read.EXIT_TIMEOUT)
        self.assertFalse(run.call_args_list[0].kwargs.get("shell", False))
        self.assertFalse(run.call_args_list[1].kwargs.get("shell", False))

    def test_nul_is_denied(self) -> None:
        with self.assertRaises(gh_read.GhReadError):
            gh_read.validate(["repo", "view", "bad\0value"])

    def test_version_drift_is_denied(self) -> None:
        wrong = SimpleNamespace(returncode=0, stdout="gh version 2.95.0\n", stderr="")
        with mock.patch.object(gh_read.subprocess, "run", return_value=wrong):
            with self.assertRaises(gh_read.GhReadError):
                gh_read.run(["repo", "view"])


if __name__ == "__main__":
    unittest.main()
