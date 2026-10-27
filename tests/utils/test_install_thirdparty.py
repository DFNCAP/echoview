import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.utils import install_thirdparty


def _app_info(root: Path) -> SimpleNamespace:
    return SimpleNamespace(application_folder=root)


@pytest.mark.parametrize(
    ("system", "executable", "expected"),
    [("Linux", "/usr/sbin/usbmuxd", True), ("Linux", None, False), ("Windows", None, True)],
)
def test_check_usbmuxd(monkeypatch: pytest.MonkeyPatch, system: str, executable: str | None, expected: bool) -> None:
    which = Mock(return_value=executable)
    monkeypatch.setattr(install_thirdparty, "SYSTEM", system)
    monkeypatch.setattr(install_thirdparty.shutil, "which", which)

    assert install_thirdparty.check_usbmuxd() is expected
    if system == "Linux":
        which.assert_called_once_with("usbmuxd")
    else:
        which.assert_not_called()


def test_unpack_scrcpy_when_already_present(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "scrcpy"
    source.mkdir()
    (source / "adb").touch()
    (source / "scrcpy").touch()
    extract = Mock()
    monkeypatch.setattr(install_thirdparty, "SYSTEM", "Linux")
    monkeypatch.setattr(install_thirdparty, "AppInfo", lambda: _app_info(tmp_path))
    monkeypatch.setattr(install_thirdparty, "extract_and_strip", extract)

    assert install_thirdparty.unpack_scrcpy() is True
    extract.assert_not_called()


def test_unpack_scrcpy_returns_false_without_archive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "scrcpy").mkdir()
    monkeypatch.setattr(install_thirdparty, "SYSTEM", "Linux")
    monkeypatch.setattr(install_thirdparty, "AppInfo", lambda: _app_info(tmp_path))

    assert install_thirdparty.unpack_scrcpy() is False


def test_unpack_goios_extracts_archive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "go-ios"
    source.mkdir()
    archive = source / "go-ios-linux.zip"
    archive.write_bytes(b"data")
    zip_file = Mock()
    zip_file.__enter__ = Mock(return_value=zip_file)
    zip_file.__exit__ = Mock(return_value=False)
    monkeypatch.setattr(install_thirdparty, "SYSTEM", "Linux")
    monkeypatch.setattr(install_thirdparty, "AppInfo", lambda: _app_info(tmp_path))
    monkeypatch.setattr(install_thirdparty.zipfile, "ZipFile", Mock(return_value=zip_file))

    assert install_thirdparty.unpack_goios() is True
    zip_file.extractall.assert_called_once_with(source)


def test_install_msi_success_and_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    run = Mock()
    monkeypatch.setattr(install_thirdparty.subprocess, "run", run)
    assert install_thirdparty.install_msi(tmp_path / "a.msi") is True

    run.side_effect = subprocess.CalledProcessError(1, "msiexec")
    assert install_thirdparty.install_msi(tmp_path / "a.msi") is False


def test_install_msi_access_denied_uses_elevation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        install_thirdparty.subprocess,
        "run",
        Mock(side_effect=subprocess.CalledProcessError(5, "msiexec")),
    )
    elevate = Mock(return_value=True)
    monkeypatch.setattr(install_thirdparty, "_elevate_and_install", elevate)
    path = tmp_path / "a.msi"

    assert install_thirdparty.install_msi(path) is True
    elevate.assert_called_once_with(path)


@pytest.mark.parametrize("system", ["Darwin", "FreeBSD"])
def test_unpackers_reject_unsupported_system(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, system: str) -> None:
    monkeypatch.setattr(install_thirdparty, "SYSTEM", system)
    monkeypatch.setattr(install_thirdparty, "AppInfo", lambda: _app_info(tmp_path))
    (tmp_path / "scrcpy").mkdir()
    (tmp_path / "go-ios").mkdir()
    (tmp_path / "uxplay").mkdir()
    assert install_thirdparty.unpack_scrcpy() is False
    assert install_thirdparty.unpack_goios() is False
    assert install_thirdparty.unpack_uxplay() is False


def test_unpack_scrcpy_extracts_archive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "scrcpy"
    source.mkdir()
    archive = source / "scrcpy-linux-v1.tar.gz"
    archive.touch()
    extract = Mock()
    monkeypatch.setattr(install_thirdparty, "SYSTEM", "Linux")
    monkeypatch.setattr(install_thirdparty, "AppInfo", lambda: _app_info(tmp_path))
    monkeypatch.setattr(install_thirdparty, "extract_and_strip", extract)
    assert install_thirdparty.unpack_scrcpy() is True
    extract.assert_called_once_with(archive, source)


@pytest.mark.parametrize(("present", "archive", "expected"), [(True, False, True), (False, False, False)])
def test_unpack_uxplay_existing_or_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, present: bool, archive: bool, expected: bool
) -> None:
    source = tmp_path / "uxplay"
    (source / "bin").mkdir(parents=True)
    if present:
        (source / "bin" / "uxplay").touch()
    if archive:
        (source / "uxplay-linux-v1.tar.gz").touch()
    monkeypatch.setattr(install_thirdparty, "SYSTEM", "Linux")
    monkeypatch.setattr(install_thirdparty, "AppInfo", lambda: _app_info(tmp_path))
    assert install_thirdparty.unpack_uxplay() is expected


def test_unpack_uxplay_extracts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "uxplay"
    source.mkdir()
    archive = source / "uxplay-linux-v1.tar.gz"
    archive.touch()
    extract = Mock()
    monkeypatch.setattr(install_thirdparty, "SYSTEM", "Linux")
    monkeypatch.setattr(install_thirdparty, "AppInfo", lambda: _app_info(tmp_path))
    monkeypatch.setattr(install_thirdparty, "extract", extract)
    assert install_thirdparty.unpack_uxplay() is True
    extract.assert_called_once_with(archive, source)


def test_unpack_wintun_linux_and_existing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(install_thirdparty, "SYSTEM", "Linux")
    assert install_thirdparty.unpack_wintun() is True
    destination = tmp_path / "go-ios" / "wintun.dll"
    destination.parent.mkdir()
    destination.touch()
    monkeypatch.setattr(install_thirdparty, "SYSTEM", "Windows")
    monkeypatch.setattr(install_thirdparty, "AppInfo", lambda: _app_info(tmp_path))
    assert install_thirdparty.unpack_wintun() is True


def test_unpack_wintun_missing_and_extracts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "go-ios").mkdir()
    source = tmp_path / "wintun"
    source.mkdir()
    monkeypatch.setattr(install_thirdparty, "SYSTEM", "Windows")
    monkeypatch.setattr(install_thirdparty, "AppInfo", lambda: _app_info(tmp_path))
    assert install_thirdparty.unpack_wintun() is False
    archive = source / "wintun-1.zip"
    archive.touch()
    zip_file = Mock()
    zip_file.__enter__ = Mock(return_value=zip_file)
    zip_file.__exit__ = Mock(return_value=False)
    zip_file.read.return_value = b"dll"
    monkeypatch.setattr(install_thirdparty.zipfile, "ZipFile", Mock(return_value=zip_file))
    assert install_thirdparty.unpack_wintun() is True
    assert (tmp_path / "go-ios" / "wintun.dll").read_bytes() == b"dll"


@pytest.mark.parametrize("installer", ["install_bonjour", "install_AppleMobileDeviceSupport"])
def test_apple_installers_skip_or_delegate(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, installer: str) -> None:
    monkeypatch.setattr(install_thirdparty, "AppInfo", lambda: _app_info(tmp_path))
    installed = Mock(return_value=True)
    install_msi = Mock(return_value=True)
    monkeypatch.setattr(install_thirdparty, "is_installed", installed)
    monkeypatch.setattr(install_thirdparty, "install_msi", install_msi)
    assert getattr(install_thirdparty, installer)() is True
    install_msi.assert_not_called()
    installed.return_value = False
    assert getattr(install_thirdparty, installer)() is True
    install_msi.assert_called_once()


def test_elevated_install_result(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    shell = Mock(return_value=33)
    ctypes = SimpleNamespace(windll=SimpleNamespace(shell32=SimpleNamespace(ShellExecuteW=shell)))
    monkeypatch.setitem(__import__("sys").modules, "ctypes", ctypes)
    assert install_thirdparty._elevate_and_install(tmp_path / "a.msi") is True
    shell.return_value = 32
    assert install_thirdparty._elevate_and_install(tmp_path / "a.msi") is False
