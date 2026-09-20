import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.utils import app_info


def _construct(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, describe: str = "v1.2.3", dirty: int = 0):
    monkeypatch.setitem(sys.modules, "__main__", SimpleNamespace(__file__=str(tmp_path / "app" / "main.py")))
    dirs = SimpleNamespace(user_data_path=tmp_path / "data", user_log_path=tmp_path / "logs")
    monkeypatch.setattr(app_info, "PlatformDirs", lambda **kwargs: dirs)
    monkeypatch.setattr(
        app_info.subprocess,
        "run",
        Mock(
            side_effect=[
                subprocess.CompletedProcess([], 0, stdout=describe),
                subprocess.CompletedProcess([], dirty),
            ]
        ),
    )
    return app_info.AppInfo()


def test_singleton_and_directories(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    info = _construct(monkeypatch, tmp_path)

    assert app_info.AppInfo() is info
    assert info.app_name == "EchoView"
    assert info.app_version == "v1.2.3"
    assert info.app_storage_folder == tmp_path / "data"
    assert info.user_log_folder == tmp_path / "logs"
    assert info.app_settings_file == tmp_path / "data" / "settings.json"
    assert info.app_storage_folder.is_dir()


def test_describe_distance_and_dirty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    info = _construct(monkeypatch, tmp_path, "v1.2.3-4-gabc123", 1)
    assert info.app_version == "v1.2.3+4+abc123.dirty"


def test_version_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setitem(sys.modules, "__main__", SimpleNamespace(__file__=str(tmp_path / "main.py")))
    dirs = SimpleNamespace(user_data_path=tmp_path / "data", user_log_path=tmp_path / "logs")
    monkeypatch.setattr(app_info, "PlatformDirs", lambda **kwargs: dirs)
    monkeypatch.setattr(app_info.subprocess, "run", Mock(side_effect=OSError("git unavailable")))

    assert app_info.AppInfo().app_version == "Unknown version"


@pytest.mark.parametrize(
    ("system", "names"),
    [
        ("Linux", ("adb", "scrcpy", "ios-amd64", "uxplay")),
        ("Windows", ("adb.exe", "scrcpy.exe", "ios.exe", "uxplay.exe")),
    ],
)
def test_platform_binary_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, system: str, names: tuple[str, str, str, str]
) -> None:
    info = _construct(monkeypatch, tmp_path)
    monkeypatch.setattr(app_info.platform, "system", lambda: system)

    assert info.adb_path.name == names[0]
    assert info.scrcpy_path.name == names[1]
    assert info.goios_path.name == names[2]
    assert info.uxplay_path.name == names[3]
