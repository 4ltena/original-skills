from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "git-read-windows.py"
SPEC = importlib.util.spec_from_file_location("git_read_windows", SCRIPT)
assert SPEC and SPEC.loader
windows = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(windows)


@unittest.skipUnless(sys.platform == "win32", "Windows entry point")
class GitReadWindowsTests(unittest.TestCase):
    def run_read(self, cwd: Path, *argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([sys.executable, "-I", str(SCRIPT), *argv], cwd=cwd, capture_output=True, text=True, encoding="utf-8")

    def test_uses_windows_binary_and_env(self) -> None:
        command, _ = windows.git_read.build_command(["status"])
        self.assertEqual(command[0], windows.GIT)
        env = windows.sanitized_env({"SYSTEMROOT": r"C:\Windows", "GIT_DIR": "x", "GH_TOKEN": "t"})
        self.assertEqual(env["PATH"], r"C:\Windows\System32;C:\Windows")
        self.assertNotIn("GIT_DIR", env)
        self.assertNotIn("GH_TOKEN", env)

    def test_fixture_reads_and_denials(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            git = [windows.GIT, "-C", str(repo)]
            subprocess.run([windows.GIT, "init", "-q", str(repo)], check=True)
            (repo / "a.txt").write_text("a\n", encoding="utf-8")
            subprocess.run([*git, "add", "a.txt"], check=True)
            subprocess.run([*git, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"], check=True)
            head = subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout

            log = self.run_read(repo, "log", "--oneline")
            self.assertEqual(log.returncode, 0, log.stderr)
            self.assertIn("init", log.stdout)
            for denied in (["commit", "-m", "x"], ["-c", "a=b", "log"], ["log", "--output=x"]):
                self.assertEqual(self.run_read(repo, *denied).returncode, 64, denied)
            self.assertEqual(subprocess.run([*git, "rev-parse", "HEAD"], capture_output=True, text=True).stdout, head)

    def test_accepts_newer_versions_only(self) -> None:
        def reported(text: str) -> SimpleNamespace:
            return SimpleNamespace(returncode=0, stdout=text, stderr="")
        for text in ("git version 2.99.0", "git version 3.0.0", "git version 2.200.1 (2027-01-01)"):
            with mock.patch.object(windows.subprocess, "run", return_value=reported(text)):
                windows.check_version({})
        for text in ("git version 2.1.0", "git version 1.99.9", "not git"):
            with mock.patch.object(windows.subprocess, "run", return_value=reported(text)):
                with self.assertRaises(windows.git_read.GitReadError):
                    windows.check_version({})


if __name__ == "__main__":
    unittest.main()
