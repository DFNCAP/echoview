import io
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.utils import generic


def test_timestamp_format() -> None:
    value = generic.get_timestamp()
    assert len(value) == 15
    assert value[8] == "_"
    assert value.replace("_", "").isdigit()


@pytest.mark.parametrize(
    ("platform", "expected"),
    [("darwin", ["open", "/tmp/item"]), ("linux", ["xdg-open", "/tmp/item"])],
)
def test_platform_specific_open(monkeypatch: pytest.MonkeyPatch, platform: str, expected: list[str]) -> None:
    popen = Mock()
    monkeypatch.setattr(generic.sys, "platform", platform)
    monkeypatch.setattr(generic, "popen", popen)

    generic.platform_specific_open("/tmp/item")

    assert popen.call_args.args[0] == expected
    if platform == "linux":
        assert popen.call_args.kwargs["env"]["LD_LIBRARY_PATH"] == ""


@pytest.mark.parametrize(("system", "command"), [("Windows", "powershell"), ("Linux", "espeak-ng")])
def test_say(monkeypatch: pytest.MonkeyPatch, system: str, command: str) -> None:
    run = Mock()
    monkeypatch.setattr(generic.platform, "system", lambda: system)
    monkeypatch.setattr(generic, "run", run)

    generic.say("hello")

    assert run.call_args.args[0][0] == command
    assert run.call_args.kwargs["check"] is True


def _create_archives(tmp_path: Path) -> tuple[Path, Path]:
    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("top/file.txt", "zip")
    tar_path = tmp_path / "sample.tar.gz"
    data = b"tar"
    with tarfile.open(tar_path, "w:gz") as archive:
        info = tarfile.TarInfo("top/file.txt")
        info.size = len(data)
        archive.addfile(info, io.BytesIO(data))
    return zip_path, tar_path


@pytest.mark.parametrize("index", [0, 1])
def test_extract_and_strip(tmp_path: Path, index: int) -> None:
    archives = _create_archives(tmp_path)
    destination = tmp_path / f"out-{index}"

    generic.extract_and_strip(archives[index], destination)

    assert (destination / "file.txt").read_text() in {"zip", "tar"}


def test_extract_and_strip_replaces_existing_file(tmp_path: Path) -> None:
    archive, _ = _create_archives(tmp_path)
    destination = tmp_path / "out"
    destination.mkdir()
    (destination / "file.txt").write_text("old")

    generic.extract_and_strip(archive, destination)

    assert (destination / "file.txt").read_text() == "zip"


def test_extract_rejects_unknown_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported archive format"):
        generic.extract(tmp_path / "archive.rar", tmp_path / "out")


def test_macos_app_is_revealed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app = tmp_path / "Example.app"
    app.mkdir()
    popen = Mock()
    monkeypatch.setattr(generic.sys, "platform", "darwin")
    monkeypatch.setattr(generic, "popen", popen)
    generic.platform_specific_open(app)
    popen.assert_called_once_with(["open", str(app), "-R"])


def test_windows_open_success(monkeypatch: pytest.MonkeyPatch) -> None:
    startfile = Mock()
    monkeypatch.setattr(generic.sys, "platform", "win32")
    monkeypatch.setattr(generic.os, "startfile", startfile, raising=False)
    generic.platform_specific_open("file.txt")
    startfile.assert_called_once_with("file.txt")


def test_windows_open_falls_back_to_notepad(monkeypatch: pytest.MonkeyPatch) -> None:
    error = OSError()
    error.winerror = -2147221003
    popen = Mock()
    monkeypatch.setattr(generic.sys, "platform", "win32")
    monkeypatch.setattr(generic.os, "startfile", Mock(side_effect=error), raising=False)
    monkeypatch.setattr(generic, "popen", popen)
    generic.platform_specific_open("file.txt")
    popen.assert_called_once_with(["notepad.exe", "file.txt"])


def test_windows_notepad_failure_shows_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    error = OSError("association")
    error.winerror = -2147221003
    warning = Mock()
    monkeypatch.setattr(generic.sys, "platform", "win32")
    monkeypatch.setattr(generic.os, "startfile", Mock(side_effect=error), raising=False)
    monkeypatch.setattr(generic, "popen", Mock(side_effect=OSError("notepad")))
    monkeypatch.setattr(generic.dialogue, "show_warning", warning)
    generic.platform_specific_open("file.xyz")
    warning.assert_called_once()
    assert warning.call_args.kwargs["details"] == str(error)


def test_windows_unrelated_error_is_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    error = OSError("denied")
    error.winerror = 5
    monkeypatch.setattr(generic.sys, "platform", "win32")
    monkeypatch.setattr(generic.os, "startfile", Mock(side_effect=error), raising=False)
    with pytest.raises(OSError, match="denied"):
        generic.platform_specific_open("file.txt")


def test_unknown_platform_does_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    popen = Mock()
    monkeypatch.setattr(generic.sys, "platform", "plan9")
    monkeypatch.setattr(generic, "popen", popen)
    generic.platform_specific_open("file.txt")
    popen.assert_not_called()


@pytest.mark.parametrize("index", [0, 1])
def test_extract_zip_and_tar(tmp_path: Path, index: int) -> None:
    archives = _create_archives(tmp_path)
    destination = tmp_path / f"extract-{index}"
    destination.mkdir()
    generic.extract(archives[index], destination)
    assert (destination / "top" / "file.txt").exists()


def test_extract_and_strip_replaces_directory(tmp_path: Path) -> None:
    archive, _ = _create_archives(tmp_path)
    destination = tmp_path / "out"
    existing = destination / "file.txt"
    existing.mkdir(parents=True)
    (existing / "old").touch()
    generic.extract_and_strip(archive, destination)
    assert (destination / "file.txt").read_text() == "zip"


def test_extract_and_strip_rejects_unknown_format(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported archive format"):
        generic.extract_and_strip(tmp_path / "archive.rar", tmp_path / "out")
