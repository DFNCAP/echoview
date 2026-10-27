"""Subprocess helpers that ensure correct behaviour on Windows without a console."""

import platform
import subprocess
from typing import Any


def run(args: Any, **kwargs: Any) -> subprocess.CompletedProcess[Any]:
    """Wrapper around subprocess.run that suppresses console window on Windows."""
    if platform.system() == "Windows":
        if "stdin" not in kwargs:
            kwargs["stdin"] = subprocess.DEVNULL
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.run(args, **kwargs)


def popen(args: Any, **kwargs: Any) -> subprocess.Popen[Any]:
    """Wrapper around subprocess.Popen that suppresses console window on Windows."""
    if platform.system() == "Windows":
        if "stdin" not in kwargs:
            kwargs["stdin"] = subprocess.DEVNULL
        if "creationflags" not in kwargs:
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    return subprocess.Popen(args, **kwargs)
