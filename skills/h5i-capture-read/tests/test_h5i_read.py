from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "h5i-read"
loader = importlib.machinery.SourceFileLoader("h5i_read", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec is not None
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)


class H5iReadPolicyTests(unittest.TestCase):
    def test_accepts_non_secret_files_of_any_type(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name in ("source.go", "asset.png", "archive.bin", "document.pdf"):
                path = root / name
                path.write_bytes(b"content")
                self.assertEqual(module.normalize_and_check_path(str(path)), path.resolve())

    def test_rejects_secret_names(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name in (".env", ".env.local", "deploy.pub", "private.pem", "credentials.json", "token.json"):
                path = root / name
                path.write_text("secret")
                with self.subTest(name=name), self.assertRaises(module.ReadPolicyError):
                    module.normalize_and_check_path(str(path))

    def test_rejects_secret_directories_and_symlink_targets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            secret_dir = root / ".ssh"
            secret_dir.mkdir()
            secret = secret_dir / "known_hosts"
            secret.write_text("secret")
            link = root / "apparently-safe.txt"
            link.symlink_to(secret)
            for path in (secret, link):
                with self.subTest(path=path), self.assertRaises(module.ReadPolicyError):
                    module.normalize_and_check_path(str(path))

    def test_accepts_only_numeric_sed_print_ranges(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "source.go"
            path.write_text("one\ntwo\n")
            command = module.build_command(["sed", "-n", "1,2p", str(path)])
            self.assertEqual(command[:3], ["/usr/bin/sed", "-n", "1,2p"])
            for script in ("1,2w out", "1e id", "/token/p"):
                with self.subTest(script=script), self.assertRaises(module.ReadPolicyError):
                    module.build_command(["sed", "-n", script, str(path)])

    def test_rejects_ripgrep_execution_and_traversal_options(self) -> None:
        for option in ("--pre=cat", "--hostname-bin=uname", "--search-zip", "-z", "--follow", "-L"):
            with self.subTest(option=option), self.assertRaises(module.ReadPolicyError):
                module.build_command(["rg", option, "pattern", "."])

    def test_ripgrep_ignores_user_config_and_excludes_secret_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "visible.txt").write_text("ok")
            command = module.build_command(["rg", "ok", str(root)])
        self.assertEqual("--no-config", command[1])
        globs = [
            command[index + 1]
            for index, value in enumerate(command[:-1])
            if value == "--glob"
        ]
        self.assertIn("!**/.env.*", globs)
        self.assertIn("!**/*.pub", globs)
        self.assertIn("!**/.ssh/**", globs)

    def test_rejects_shells_dispatchers_and_unbounded_tail(self) -> None:
        for program in ("bash", "sh", "zsh", "env", "xargs"):
            with self.subTest(program=program), self.assertRaises(module.ReadPolicyError):
                module.build_command([program, "anything"])
        with self.assertRaises(module.ReadPolicyError):
            module.build_command(["tail", "-f", "file"])
        with self.assertRaises(module.ReadPolicyError):
            module.build_command(["tail", "--follow=name", "file"])

    def test_accepts_bounded_nl_and_rejects_unknown_options(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "source.go"
            path.write_text("one\ntwo\n")
            for args in (["-ba"], ["-b", "a"], ["-nrz"], ["--number-format=rz"]):
                with self.subTest(args=tuple(args)):
                    command = module.build_command(["nl", *args, str(path)])
                    self.assertEqual(command[0], "/usr/bin/nl")
            for args in (["-Z"], ["--write=out"], ["-p2"]):
                with self.subTest(args=tuple(args)), self.assertRaises(module.ReadPolicyError):
                    module.build_command(["nl", *args, str(path)])
            with self.assertRaises(module.ReadPolicyError):
                module.build_command(["nl", "-ba"])

    def test_nl_rejects_secret_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / ".env"
            path.write_text("secret")
            with self.assertRaises(module.ReadPolicyError):
                module.build_command(["nl", "-ba", str(path)])

    def test_grep_treats_the_first_positional_as_the_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "source.go").write_text("needle\n")
            command = module.build_command(
                ["grep", "-n", "-A", "3", "needle", str(root / "source.go")]
            )
            self.assertEqual(command[0], "/usr/bin/grep")
            self.assertNotIn("--exclude-dir=.ssh", command)
            with self.assertRaises(module.ReadPolicyError):
                module.build_command(["grep", "needle"])

    def test_grep_rejects_traversal_and_device_options(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "source.go").write_text("needle\n")
            for option in ("-R", "--dereference-recursive", "-D", "--devices=read", "-d", "--directories=read", "-Q"):
                with self.subTest(option=option), self.assertRaises(module.ReadPolicyError):
                    module.build_command(["grep", option, "needle", str(root)])

    def test_recursive_grep_injects_secret_exclusions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "source.go").write_text("needle\n")
            command = module.build_command(["grep", "-rn", "needle", str(root)])
            self.assertIn("--exclude=.env", command)
            self.assertIn("--exclude=*.pub", command)
            self.assertIn("--exclude-dir=.ssh", command)

    def test_grep_pattern_file_is_path_checked(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "source.go").write_text("needle\n")
            (root / ".env").write_text("secret")
            with self.assertRaises(module.ReadPolicyError):
                module.build_command(["grep", "-f", str(root / ".env"), str(root)])

    def test_find_accepts_only_read_only_predicates(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "source.go").write_text("ok")
            command = module.build_command(
                ["find", str(root), "-maxdepth", "2", "-type", "f", "-name", "*.go", "-print"]
            )
            self.assertEqual(command[0], "/usr/bin/find")
            for predicate in ("-exec", "-execdir", "-ok", "-delete", "-fprint", "-fprintf", "-print0", "-L", "-follow"):
                with self.subTest(predicate=predicate), self.assertRaises(module.ReadPolicyError):
                    module.build_command(["find", str(root), predicate, "rm"])
            with self.assertRaises(module.ReadPolicyError):
                module.build_command(["find", "-name", "x"])

    def test_find_output_drops_secret_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "visible.txt").write_text("ok")
            (root / "private.pem").write_text("secret")
            command = module.build_command(["find", str(root), "-type", "f", "-print"])
            with mock.patch.object(module.subprocess, "run") as run:
                run.return_value.returncode = 0
                run.return_value.stdout = "\n".join(
                    [str(root / "visible.txt"), str(root / "private.pem")]
                )
                run.return_value.stderr = ""
                with mock.patch.object(module, "print") as printed:
                    self.assertEqual(module._run_with_secret_filter(command, {}), 0)
            emitted = [call.args[0] for call in printed.call_args_list]
            self.assertIn(str(root / "visible.txt"), emitted)
            self.assertNotIn(str(root / "private.pem"), emitted)

    def test_run_executes_only_the_validated_argv_without_a_shell(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "source.go"
            path.write_text("package example\n")
            with mock.patch.object(module.subprocess, "run") as run:
                run.return_value.returncode = 0
                self.assertEqual(module.run(["cat", str(path)]), 0)
            called = run.call_args.args[0]
            self.assertEqual(called, ["/bin/cat", str(path)])
            self.assertNotIn("shell", run.call_args.kwargs)

    def test_listing_filters_secret_entries(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "visible.txt").write_text("ok")
            (root / ".env").write_text("secret")
            lines = list(module._format_listing(root, include_hidden=True, recursive=True))
            self.assertTrue(any("visible.txt" in line for line in lines))
            self.assertFalse(any(".env" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
