from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "gh-read-windows.py"
SPEC = importlib.util.spec_from_file_location("gh_read_windows", SCRIPT)
assert SPEC and SPEC.loader
windows = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(windows)


@unittest.skipUnless(sys.platform == "win32", "Windows entry point")
class GhReadWindowsTests(unittest.TestCase):
    def run_read(self, *argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *argv], capture_output=True, text=True, encoding="utf-8")

    def test_uses_windows_binary_and_env(self) -> None:
        self.assertEqual(windows.gh_read.validate(["pr", "list"])[0], windows.GH)
        env = windows.sanitized_env({"SYSTEMROOT": r"C:\Windows", "APPDATA": "a", "GH_TOKEN": "t", "GIT_DIR": "x"})
        self.assertEqual(env["PATH"], r"C:\Windows\System32;C:\Windows")
        self.assertEqual((env["APPDATA"], env["GH_TOKEN"]), ("a", "t"))
        self.assertNotIn("GIT_DIR", env)

    def test_denials_run_before_gh(self) -> None:
        for denied in (["api", "user"], ["pr", "list", "--web"], ["pr", "merge", "1"], ["repo", "view", "-R", "https://x/y"]):
            self.assertEqual(self.run_read(*denied).returncode, 64, denied)

    def test_version_pin_matches_installed_gh(self) -> None:
        windows.gh_read._check_version(windows.sanitized_env())

    def test_accepts_newer_versions_only(self) -> None:
        def reported(text: str) -> SimpleNamespace:
            return SimpleNamespace(returncode=0, stdout=text, stderr="")
        for text in ("gh version 2.99.0", "gh version 3.0.0", "gh version 2.200.1 (2027-01-01)"):
            with mock.patch.object(windows.subprocess, "run", return_value=reported(text)):
                windows.check_version({})
        for text in ("gh version 2.1.0", "gh version 1.99.9", "not gh"):
            with mock.patch.object(windows.subprocess, "run", return_value=reported(text)):
                with self.assertRaises(windows.gh_read.GhReadError):
                    windows.check_version({})


if __name__ == "__main__":
    unittest.main()
