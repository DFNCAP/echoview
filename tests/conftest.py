import os
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.devices.android import AndroidDevice
from app.devices.devices import ConnectionType
from app.devices.ios import iOSDevice
from app.utils.app_info import AppInfo


class FakeSignal:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def emit(self, *args: Any) -> None:
        self.calls.append(args)


class FakeReporter:
    def __init__(self) -> None:
        self.status_changed = FakeSignal()
        self.progress_changed = FakeSignal()


class FakeProcess:
    def __init__(
        self,
        stdout: bytes | str = b"",
        stderr: bytes | str = b"",
        polls: list[int | None] | None = None,
        pid: int = 123,
    ) -> None:
        self.stdout = (
            SimpleNamespace(read=lambda: stdout) if isinstance(stdout, bytes) else iter(stdout.splitlines(True))
        )
        self.stderr = SimpleNamespace(read=lambda: stderr)
        self.pid = pid
        self._polls = iter(polls or [0])
        self.terminated = False
        self.killed = False
        self.wait_calls: list[int | None] = []

    def poll(self) -> int | None:
        return next(self._polls, 0)

    def wait(self, timeout: int | None = None) -> int:
        self.wait_calls.append(timeout)
        return 0

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True


@pytest.fixture(autouse=True)
def reset_app_info() -> Iterator[None]:
    AppInfo._instance = None
    yield
    AppInfo._instance = None


@pytest.fixture
def completed_process() -> Callable[..., subprocess.CompletedProcess[Any]]:
    def factory(stdout: Any = "", stderr: Any = "", returncode: int = 0) -> subprocess.CompletedProcess[Any]:
        return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr=stderr)

    return factory


@pytest.fixture
def fake_reporter() -> FakeReporter:
    return FakeReporter()


@pytest.fixture
def android_device() -> AndroidDevice:
    return AndroidDevice(
        identifier="android-1",
        serial="android-1",
        device_name="Pixel",
        os="Android",
        os_version="15",
        device_type="Pixel 9",
        width=1080,
        height=1920,
        connection_type=ConnectionType.FULL,
    )


@pytest.fixture
def ios_device() -> iOSDevice:
    return iOSDevice(
        identifier="ios-1",
        serial="serial-1",
        device_name="iPhone",
        os="iOS",
        os_version="17.5",
        device_type="iPhone 15",
        connection_type=ConnectionType.FULL,
    )


@pytest.fixture
def app_info_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Mock:
    stub = Mock()
    stub.application_folder = tmp_path
    stub.app_storage_folder = tmp_path / "data"
    stub.user_log_folder = tmp_path / "logs"
    stub.app_settings_file = stub.app_storage_folder / "settings.json"
    stub.app_name = "EchoView"
    stub.app_version = "test"
    stub.adb_path = tmp_path / "adb"
    stub.scrcpy_path = tmp_path / "scrcpy"
    stub.goios_path = tmp_path / "go-ios"
    stub.uxplay_path = tmp_path / "uxplay"
    monkeypatch.setattr("app.utils.app_info.AppInfo", lambda: stub)
    return stub
