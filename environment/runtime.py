"""Verified interpreter binding and host-specific command generation (stdlib)."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys


def probe(executable=None):
    candidate = str(Path(executable or sys.executable).expanduser().absolute())
    if "windowsapps" in candidate.lower():
        raise ValueError("WindowsApps Python aliases are not interpreters")
    result = subprocess.run([candidate, "-I", "-X", "utf8", "-c",
        "import sys,json;print(json.dumps({'version':list(sys.version_info[:3]),"
        "'executable':sys.executable,'platform':sys.platform}))"],
        capture_output=True, text=True, encoding="utf-8", timeout=10, check=True)
    value = json.loads(result.stdout)
    version = value.get("version")
    actual = value.get("executable")
    if (not isinstance(version, list) or len(version) != 3
            or any(type(n) is not int for n in version) or version[:2] < [3, 10]
            or value.get("platform") not in {"win32", "darwin", "linux"}
            or not isinstance(actual, str) or not Path(actual).is_absolute()
            or "windowsapps" in actual.lower()):
        raise ValueError("Python 3.10+ probe failed")
    if Path(actual).resolve() != Path(candidate).resolve():
        raise ValueError("interpreter returned a different executable")
    return value


def command(argv, platform=None):
    """Windows hooks use cmd.exe; reject expansion characters rather than guess."""
    platform = platform or sys.platform
    argv = [str(arg) for arg in argv]
    if any(any(c in arg for c in ("\0", "\n", "\r")) for arg in argv):
        raise ValueError("NUL/newline in command")
    if platform == "win32":
        if any(any(c in arg for c in ('"', "%", "!", "&", "|", "<", ">", "^"))
               or arg.endswith("\\") for arg in argv):
            raise ValueError("path cannot be represented safely in a Windows hook")
        return " ".join('"' + arg + '"' for arg in argv)
    return shlex.join(argv)


def python_command(binding, script, *args):
    return command([binding["executable"], "-X", "utf8", "-B", script, *args], binding["platform"])


def safe_path(path):
    path = Path(path).expanduser().absolute()
    if '..' in path.parts:
        raise ValueError('parent traversal in installation path')
    for part in [*reversed(path.parents), path]:
        if part.is_symlink():
            raise ValueError("symlink in installation path: " + str(part))
        if part.exists():
            info = part.lstat()
            if getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("reparse point in installation path")
    return path
