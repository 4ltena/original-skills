from __future__ import annotations

import importlib.util
import importlib.machinery
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "h5i-read"
LOADER = importlib.machinery.SourceFileLoader("h5i_read", str(SCRIPT))
SPEC = importlib.util.spec_from_loader("h5i_read", LOADER)
assert SPEC and SPEC.loader
h5i_read = importlib.util.module_from_spec(SPEC)
sys.modules["h5i_read"] = h5i_read
SPEC.loader.exec_module(h5i_read)


class H5iReadTests(unittest.TestCase):
    def test_capture_builds_exact_fixed_child_command(self) -> None:
        command, timeout = h5i_read.validate(["capture", "sed", "-n", "1,2p", "README.md"])
        self.assertEqual(command, [
            h5i_read.H5I, "capture", "run", "--", h5i_read.CAPTURE_READER,
            "sed", "-n", "1,2p", "README.md",
        ])
        self.assertEqual(timeout, 600)

    def test_positive_command_paths(self) -> None:
        cases = [
            ["recall", "log"], ["recall", "context"], ["audit", "review"],
            ["audit", "policy", "show"], ["env", "doctor"], ["team", "status"],
            ["msg", "history"], ["policy", "check"], ["objects", "list"],
            ["log"], ["context", "show"], ["notes", "coverage"], ["memory", "diff"],
        ]
        for argv in cases:
            with self.subTest(argv=argv):
                command, _ = h5i_read.validate(argv)
                self.assertEqual(command, [h5i_read.H5I, *argv])
        self.assertEqual(h5i_read._validate_gc(["objects", "gc", "--dry-run"])[0], [h5i_read.H5I, "objects", "gc", "--dry-run"])

    def test_raw_object_reads_are_denied(self) -> None:
        denied = [
            ["recall", "object", "abc"],
            ["objects", "get", "abc"],
            ["objects", "get", "abc", "--summary", "--manifest"],
        ]
        for argv in denied:
            with self.subTest(argv=argv), self.assertRaises(h5i_read.H5iReadError):
                h5i_read.validate(argv)
        self.assertEqual(h5i_read.validate(["objects", "get", "abc", "--summary"])[0], [h5i_read.H5I, "objects", "get", "abc", "--summary"])

    def test_dangerous_and_unknown_arguments_are_denied(self) -> None:
        for argv in (
            ["objects", "fsck", "--repair"], ["objects", "filters", "--verify"],
            ["team", "status", "--force"], ["log", "--output", "x"],
            ["log", "--pager"], ["log", "--unknown"], ["log", "--", "repair"], ["log", "--", "--repair"],
            ["policy", "init"], ["team", "bootstrap", "extra"],
        ):
            with self.subTest(argv=argv), self.assertRaises(h5i_read.H5iReadError):
                h5i_read.validate(argv)

    def test_environment_is_allowlisted_and_sanitized(self) -> None:
        env = h5i_read.sanitized_env({
            "HOME": "/tmp/home", "USER": "u", "GH_TOKEN": "secret", "GIT_EDITOR": "bad",
            "PAGER": "less", "PATH": "/bad",
        })
        self.assertEqual(env["HOME"], "/tmp/home")
        self.assertEqual(env["GIT_PAGER"], "cat")
        self.assertEqual(env["PAGER"], "cat")
        self.assertNotIn("GH_TOKEN", env)
        self.assertNotIn("GIT_EDITOR", env)
        self.assertEqual(env["PATH"], "/home/altena/.codex/packages/standalone/releases/0.156.1-x86_64-unknown-linux-musl/codex-path:/usr/bin:/bin:/usr/sbin:/sbin")

    def test_run_uses_no_shell_and_reports_timeout(self) -> None:
        version = SimpleNamespace(returncode=0, stdout="h5i 0.2.8\n", stderr="")
        with mock.patch.object(h5i_read.subprocess, "run", side_effect=[version, subprocess.TimeoutExpired([h5i_read.H5I], 120)]) as run:
            self.assertEqual(h5i_read.run(["log"]), h5i_read.EXIT_TIMEOUT)
        self.assertFalse(run.call_args_list[0].kwargs.get("shell", False))
        self.assertFalse(run.call_args_list[1].kwargs.get("shell", False))

    def test_version_drift_is_denied(self) -> None:
        wrong = SimpleNamespace(returncode=0, stdout="h5i 0.3.0\n", stderr="")
        with mock.patch.object(h5i_read.subprocess, "run", return_value=wrong):
            with self.assertRaises(h5i_read.H5iReadError):
                h5i_read.run(["log"])

    def test_nul_is_denied(self) -> None:
        with self.assertRaises(h5i_read.H5iReadError):
            h5i_read.validate(["log", "bad\0value"])


if __name__ == "__main__":
    unittest.main()
