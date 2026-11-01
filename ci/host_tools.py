"""Choose an existing Bash without accidentally selecting Windows' WSL shim."""
import os
from pathlib import Path
import shutil


def select_bash(environ=None, windows=None):
    env = os.environ if environ is None else environ
    windows = os.name == "nt" if windows is None else windows
    override = env.get("TEST_BASH")
    if override:
        resolved = override if Path(override).is_file() else shutil.which(override, path=env.get("PATH"))
        if not resolved:
            raise RuntimeError("TEST_BASH does not name an existing executable")
        return str(resolved)
    if windows:
        for variable in ("ProgramFiles", "ProgramW6432", "ProgramFiles(x86)"):
            if env.get(variable):
                candidate = Path(env[variable]) / "Git/bin/bash.exe"
                if candidate.is_file():
                    return str(candidate)
        raise RuntimeError("Git Bash is required on Windows; set TEST_BASH to its bash.exe. The WSL shim is not selected.")
    resolved = shutil.which("bash", path=env.get("PATH"))
    if not resolved:
        raise RuntimeError("Bash is required; set TEST_BASH to an existing supported executable")
    return resolved
