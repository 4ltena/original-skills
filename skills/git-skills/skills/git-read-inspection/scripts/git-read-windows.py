"""Windows entry point for git-read: same validator, Windows Git binary and environment.

The argv grammar, forbidden options and fixed config live in the sibling `git-read`
script and are loaded unchanged; only the binary, version check and environment differ.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Mapping

_SCRIPT = Path(__file__).with_name("git-read")
_LOADER = importlib.machinery.SourceFileLoader("git_read", str(_SCRIPT))
_SPEC = importlib.util.spec_from_loader("git_read", _LOADER)
assert _SPEC and _SPEC.loader
git_read = importlib.util.module_from_spec(_SPEC)
sys.modules["git_read"] = git_read  # dataclasses resolve the module through sys.modules
_SPEC.loader.exec_module(git_read)

GIT = r"C:\Program Files\Git\cmd\git.exe"
# Oldest release the grammar was checked against. Newer releases are accepted so updates do not
# lock reads out; options they add stay denied because the grammar is an allow-list.
MINIMUM_VERSION = (2, 54, 0)

# Windows needs these for process start-up, HOME resolution and temp files; nothing else is inherited.
WINDOWS_KEYS = (
    "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
    "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "TEMP", "TMP", "LANG", "LC_ALL", "LC_CTYPE", "TERM",
)


def sanitized_env(source: Mapping[str, str] | None = None) -> dict[str, str]:
    inherited = os.environ if source is None else source
    env = {key: inherited[key] for key in WINDOWS_KEYS if key in inherited}
    root = env.get("SYSTEMROOT", r"C:\Windows")
    env.update({
        "PATH": rf"{root}\System32;{root}",
        "GIT_ATTR_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "NUL", "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat", "PAGER": "cat",
    })
    return env


def trusted_directories() -> list[str]:
    """safe.directory entries from the user's own global config.

    Drives such as exFAT record no owner, so Git refuses them unless trusted. The read env
    ignores global config, so only these explicit trust entries are forwarded via -c.
    """
    env = sanitized_env()
    env.pop("GIT_CONFIG_GLOBAL")
    try:
        result = subprocess.run(
            [GIT, "config", "--global", "--get-all", "safe.directory"],
            capture_output=True, text=True, encoding="utf-8", check=False, timeout=10, env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [line for line in result.stdout.splitlines() if line]


def check_version(env: Mapping[str, str]) -> None:
    try:
        result = subprocess.run([GIT, "version"], capture_output=True, text=True, check=False, timeout=10, env=dict(env))
    except (OSError, subprocess.TimeoutExpired) as error:
        raise git_read.GitReadError("unable to verify git version") from error
    match = re.match(r"git version (\d+)\.(\d+)\.(\d+)", (result.stdout or result.stderr).strip())
    if result.returncode != 0 or not match or tuple(map(int, match.groups())) < MINIMUM_VERSION:
        raise git_read.GitReadError("unsupported git version")


git_read.GIT = GIT
git_read._check_version = check_version
git_read.sanitized_env = sanitized_env
for _directory in trusted_directories():
    git_read.FIXED_CONFIG += ["-c", f"safe.directory={_directory}"]

if __name__ == "__main__":
    raise SystemExit(git_read.main())
