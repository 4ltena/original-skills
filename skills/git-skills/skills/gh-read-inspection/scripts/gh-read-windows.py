"""Windows entry point for gh-read: same validator, Windows gh binary and environment.

The command grammar and forbidden options live in the sibling `gh-read` script and are
loaded unchanged; only the binary, version check and environment differ.
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

_SCRIPT = Path(__file__).with_name("gh-read")
_LOADER = importlib.machinery.SourceFileLoader("gh_read", str(_SCRIPT))
_SPEC = importlib.util.spec_from_loader("gh_read", _LOADER)
assert _SPEC and _SPEC.loader
gh_read = importlib.util.module_from_spec(_SPEC)
sys.modules["gh_read"] = gh_read  # dataclasses resolve the module through sys.modules
_SPEC.loader.exec_module(gh_read)

GH = r"C:\Program Files\GitHub CLI\gh.exe"
# Oldest release the grammar was checked against. Newer releases are accepted so updates do not
# lock reads out; options they add stay denied because the grammar is an allow-list.
MINIMUM_VERSION = (2, 93, 0)

# APPDATA/USERPROFILE locate gh's config and the Credential Manager login; tokens and proxies as on Linux.
WINDOWS_KEYS = (
    "SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "USERPROFILE", "HOMEDRIVE", "HOMEPATH",
    "APPDATA", "LOCALAPPDATA", "PROGRAMDATA", "TEMP", "TMP", "LANG", "LC_ALL", "LC_CTYPE", "TERM",
    "GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN", "GH_REPO",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR",
)


def sanitized_env(source: Mapping[str, str] | None = None) -> dict[str, str]:
    inherited = os.environ if source is None else source
    env = {key: inherited[key] for key in WINDOWS_KEYS if key in inherited}
    root = env.get("SYSTEMROOT", r"C:\Windows")
    env.update({
        "PATH": rf"{root}\System32;{root}",
        "GH_PAGER": "cat", "PAGER": "cat", "GH_PROMPT_DISABLED": "1", "NO_COLOR": "1",
    })
    return env


def check_version(env: Mapping[str, str]) -> None:
    try:
        result = subprocess.run([GH, "version"], capture_output=True, text=True, check=False, timeout=10, env=dict(env))
    except (OSError, subprocess.TimeoutExpired) as error:
        raise gh_read.GhReadError("unable to verify gh version") from error
    match = re.match(r"gh version (\d+)\.(\d+)\.(\d+)", (result.stdout or result.stderr).strip())
    if result.returncode != 0 or not match or tuple(map(int, match.groups())) < MINIMUM_VERSION:
        raise gh_read.GhReadError("unsupported gh version")


gh_read.GH = GH
gh_read._check_version = check_version
gh_read.sanitized_env = sanitized_env

if __name__ == "__main__":
    raise SystemExit(gh_read.main())
