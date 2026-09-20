import subprocess
from unittest.mock import Mock

import pytest

from app.utils import subprocess_helpers


@pytest.mark.parametrize(
    ("helper", "target"), [(subprocess_helpers.run, "subprocess.run"), (subprocess_helpers.popen, "subprocess.Popen")]
)
def test_non_windows_passes_arguments_through(monkeypatch: pytest.MonkeyPatch, helper, target: str) -> None:
    call = Mock(return_value=object())
    monkeypatch.setattr(subprocess_helpers.platform, "system", lambda: "Linux")
    monkeypatch.setattr(target, call)

    result = helper(["tool"], text=True)

    assert result is call.return_value
    call.assert_called_once_with(["tool"], text=True)


@pytest.mark.parametrize(
    ("helper", "target"), [(subprocess_helpers.run, "subprocess.run"), (subprocess_helpers.popen, "subprocess.Popen")]
)
def test_windows_adds_console_suppression(monkeypatch: pytest.MonkeyPatch, helper, target: str) -> None:
    call = Mock(return_value=object())
    monkeypatch.setattr(subprocess_helpers.platform, "system", lambda: "Windows")
    monkeypatch.setattr(subprocess_helpers.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
    monkeypatch.setattr(target, call)

    helper(["tool"])

    call.assert_called_once_with(["tool"], stdin=subprocess.DEVNULL, creationflags=0x08000000)


def test_windows_preserves_explicit_options(monkeypatch: pytest.MonkeyPatch) -> None:
    call = Mock(return_value=object())
    monkeypatch.setattr(subprocess_helpers.platform, "system", lambda: "Windows")
    monkeypatch.setattr(subprocess_helpers.subprocess, "run", call)

    subprocess_helpers.run(["tool"], stdin=subprocess.PIPE, creationflags=99)

    call.assert_called_once_with(["tool"], stdin=subprocess.PIPE, creationflags=99)
