import threading
from pathlib import Path
from unittest.mock import Mock, call

import pytest

from app.devices import android
from app.devices.devices import ConnectionType


def test_device_info(android_device) -> None:
    assert android_device.get_info() == "Android - Pixel (android-1)"


def test_get_connected_devices(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    monkeypatch.setattr(
        android,
        "run",
        Mock(return_value=completed_process("List of devices attached\nfull\tdevice\nlocked\tunauthorized\n")),
    )
    monkeypatch.setattr(android, "get_setting", lambda *args: "Pixel")
    monkeypatch.setattr(android, "get_property", lambda serial, prop: "15" if "release" in prop else "Pixel 9")
    monkeypatch.setattr(android, "get_window_size", lambda *args: (1080, 1920))

    devices = android.get_connected_devices()

    assert [device.identifier for device in devices] == ["full", "locked"]
    assert devices[0].connection_type is ConnectionType.FULL
    assert devices[0].device_name == "Pixel"
    assert devices[1].connection_type is ConnectionType.NONE


def test_get_contacts_parses_and_filters(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    output = "Row: 0 display_name=Alice, data1=0400\nRow: 1 display_name=Same, data1=Same\n"
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    monkeypatch.setattr(android, "run", Mock(return_value=completed_process(output)))
    assert android.get_contacts("serial") == [("Alice", "0400")]


def test_get_contacts_handles_no_results(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    monkeypatch.setattr(android, "run", Mock(return_value=completed_process("No result found.")))
    assert android.get_contacts("serial") == []


def test_package_and_directory_parsers(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    monkeypatch.setattr(android, "run", Mock(return_value=completed_process("package:one\npackage:two\n")))
    assert android.list_installed_packages("serial") == ["one", "two"]
    assert android.list_system_packages("serial") == ["one", "two"]
    assert android.ls("serial", "/sdcard") == ["/sdcard/package:one", "/sdcard/package:two"]


def test_screenshot_writes_output(monkeypatch: pytest.MonkeyPatch, completed_process, tmp_path: Path) -> None:
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    monkeypatch.setattr(android, "run", Mock(return_value=completed_process(b"png")))
    output = tmp_path / "nested" / "screen.png"
    assert android.screenshot("serial", output) == output
    assert output.read_bytes() == b"png"


@pytest.mark.parametrize(
    ("direction", "coordinates"),
    [
        ("up", ["500", "250", "500", "1000"]),
        ("down", ["500", "750", "500", "0"]),
        ("left", ["250", "500", "1000", "500"]),
        ("right", ["750", "500", "0", "500"]),
    ],
)
def test_scroll_coordinates(
    monkeypatch: pytest.MonkeyPatch, completed_process, direction: str, coordinates: list[str]
) -> None:
    run = Mock(return_value=completed_process(stderr=""))
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    monkeypatch.setattr(android, "run", run)
    assert android.scroll("serial", direction, 1000, 1000) is True
    assert run.call_args.args[0][6:10] == coordinates


def test_scroll_rejects_invalid_direction(monkeypatch: pytest.MonkeyPatch) -> None:
    run = Mock()
    monkeypatch.setattr(android, "run", run)
    assert android.scroll("serial", "diagonal", 100, 100) is False
    run.assert_not_called()


def test_extract_contacts_and_missing_contacts(monkeypatch: pytest.MonkeyPatch, android_device, tmp_path: Path) -> None:
    monkeypatch.setattr(android, "get_contacts", lambda *args: [("Alice", "0400")])
    output = android_device.extract_contacts(tmp_path / "contacts" / "contacts.txt")
    assert output.read_text() == "Alice : 0400\n"
    monkeypatch.setattr(android, "get_contacts", lambda *args: [])
    with pytest.raises(android.NoContactsFoundError):
        android_device.extract_contacts(tmp_path / "empty.txt")


def test_backup_dispatches_items_and_reports(
    monkeypatch: pytest.MonkeyPatch, android_device, fake_reporter, tmp_path: Path
) -> None:
    monkeypatch.setattr(android, "list_installed_packages", lambda *args: ["user.app"])
    monkeypatch.setattr(android, "list_system_packages", lambda *args: ["system.app"])
    monkeypatch.setattr(android, "ls", lambda *args: ["/sdcard/DCIM"])
    dump_apk = Mock()
    dump = Mock()
    monkeypatch.setattr(android, "dump_apk", dump_apk)
    monkeypatch.setattr(android, "dump", dump)

    assert android_device.backup(tmp_path, fake_reporter) == tmp_path
    assert dump_apk.call_args_list == [
        call("android-1", "user.app", tmp_path / "installed_packages"),
        call("android-1", "system.app", tmp_path / "system_packages"),
    ]
    dump.assert_called_once_with("android-1", "/sdcard/DCIM", tmp_path / "sdcard")
    assert fake_reporter.progress_changed.calls[-1] == ("android-1", 3, 3)


def test_backup_honours_cancellation(monkeypatch: pytest.MonkeyPatch, android_device, tmp_path: Path) -> None:
    monkeypatch.setattr(android, "list_installed_packages", lambda *args: ["app"])
    monkeypatch.setattr(android, "list_system_packages", lambda *args: [])
    monkeypatch.setattr(android, "ls", lambda *args: [])
    dump = Mock()
    monkeypatch.setattr(android, "dump_apk", dump)
    cancelled = threading.Event()
    cancelled.set()
    assert android_device.backup(tmp_path, cancelled=cancelled) == Path()
    dump.assert_not_called()


def test_screen_recording_lifecycle(monkeypatch: pytest.MonkeyPatch, android_device, tmp_path: Path) -> None:
    process = Mock(pid=10)
    process.wait = Mock()
    monkeypatch.setattr(android, "_scrcpy", lambda: "scrcpy")
    popen = Mock(return_value=process)
    monkeypatch.setattr(android, "popen", popen)
    android_device.start_screen_recording(tmp_path / "recordings" / "a.mp4")
    assert android_device.recording_process is None
    assert "--record" in popen.call_args.args[0]


def test_stop_screen_recording_non_windows(monkeypatch: pytest.MonkeyPatch, android_device) -> None:
    process = Mock()
    android_device.recording_process = process
    monkeypatch.setattr(android.platform, "system", lambda: "Linux")
    android_device.stop_screen_recording()
    process.terminate.assert_called_once()


def test_extract_device_info_writes_artifacts(
    monkeypatch: pytest.MonkeyPatch, completed_process, android_device, fake_reporter, tmp_path: Path
) -> None:
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    run = Mock(
        side_effect=[
            completed_process(b"props"),
            completed_process(b"system"),
            completed_process(b"secure"),
            completed_process(b"global"),
        ]
    )
    monkeypatch.setattr(android, "run", run)
    monkeypatch.setattr(android, "list_installed_packages", lambda *args: ["third.party"])
    monkeypatch.setattr(android, "list_system_packages", lambda *args: ["system.app"])
    android_device.extract_device_info(tmp_path, fake_reporter)
    assert (tmp_path / "getprop_raw.txt").read_bytes() == b"props"
    assert (tmp_path / "system_settings_raw.txt").read_bytes() == b"system"
    assert (tmp_path / "secure_settings_raw.txt").read_bytes() == b"secure"
    assert (tmp_path / "global_settings_raw.txt").read_bytes() == b"global"
    assert (tmp_path / "third_party_apps.log").read_text() == "third.party"
    assert (tmp_path / "system_apps.log").read_text() == "system.app"
    assert fake_reporter.progress_changed.calls[-1] == ("android-1", 4, 4)


def test_extract_device_info_skips_empty_outputs(
    monkeypatch: pytest.MonkeyPatch, completed_process, android_device, tmp_path: Path
) -> None:
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    monkeypatch.setattr(android, "run", Mock(return_value=completed_process(b"")))
    monkeypatch.setattr(android, "list_installed_packages", lambda *args: [])
    monkeypatch.setattr(android, "list_system_packages", lambda *args: [])
    android_device.extract_device_info(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_extract_device_logs_writes_all_outputs(
    monkeypatch: pytest.MonkeyPatch, completed_process, android_device, fake_reporter, tmp_path: Path
) -> None:
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    dumpsys = Mock()
    dumpsys.poll.return_value = 0
    dumpsys.stdout.read.return_value = b"dumpsys"
    bugreport = Mock()
    bugreport.poll.return_value = 0
    monkeypatch.setattr(android, "popen", Mock(side_effect=[dumpsys, bugreport]))
    monkeypatch.setattr(
        android,
        "run",
        Mock(side_effect=[completed_process(b"stats"), completed_process(b"logs")]),
    )
    android_device.extract_device_logs(tmp_path, fake_reporter)
    assert (tmp_path / "dumpsys.log").read_bytes() == b"dumpsys"
    assert (tmp_path / "logcat_stats.log").read_bytes() == b"stats"
    assert (tmp_path / "logcat_log.log").read_bytes() == b"logs"
    assert fake_reporter.progress_changed.calls[-1] == ("android-1", 4, 4)


def test_extract_device_logs_cancels_running_process(
    monkeypatch: pytest.MonkeyPatch, android_device, tmp_path: Path
) -> None:
    process = Mock()
    process.poll.return_value = None
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    monkeypatch.setattr(android, "popen", Mock(return_value=process))
    cancelled = threading.Event()
    monkeypatch.setattr(android.time, "sleep", lambda _: cancelled.set())
    android_device.extract_device_logs(tmp_path, cancelled=cancelled)
    process.kill.assert_called_once()
    process.wait.assert_called_once()


def test_dump_and_backup_commands(monkeypatch: pytest.MonkeyPatch, completed_process, tmp_path: Path) -> None:
    run = Mock(return_value=completed_process())
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    monkeypatch.setattr(android, "run", run)
    android.dump("serial", "/sdcard/DCIM", tmp_path / "dump")
    assert (tmp_path / "dump").is_dir()
    assert run.call_args.args[0][3:5] == ["pull", "/sdcard/DCIM"]
    output = android.backup("serial", tmp_path / "backup" / "a.ab")
    assert output.parent.is_dir()
    assert "backup" in run.call_args.args[0]


def test_package_helpers_and_values(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    run = Mock(
        side_effect=[
            completed_process("package:one\n"),
            completed_process(" value \n"),
            completed_process(" property \n"),
            completed_process("Physical size: 1080x1920\n"),
            completed_process(""),
        ]
    )
    monkeypatch.setattr(android, "run", run)
    assert android.list_all_packages("serial", "-3") == ["one"]
    assert android.get_setting("serial", "global", "name") == "value"
    assert android.get_property("serial", "prop") == "property"
    assert android.get_window_size("serial") == (1080, 1920)
    assert android.get_window_size("serial") == (0, 0)


def test_dump_apk_empty_and_multiple_paths(monkeypatch: pytest.MonkeyPatch, completed_process, tmp_path: Path) -> None:
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    run = Mock(
        side_effect=[
            completed_process(""),
            completed_process("package:/base.apk\npackage:/split.apk\n"),
            completed_process(),
            completed_process(),
        ]
    )
    monkeypatch.setattr(android, "run", run)
    android.dump_apk("serial", "empty", tmp_path)
    assert not (tmp_path / "empty").exists()
    android.dump_apk("serial", "app", tmp_path)
    assert (tmp_path / "app").is_dir()
    assert run.call_count == 4


def test_windows_stop_and_kill_server(monkeypatch: pytest.MonkeyPatch, completed_process, android_device) -> None:
    process = Mock(pid=44)
    android_device.recording_process = process
    run = Mock(return_value=completed_process())
    monkeypatch.setattr(android.platform, "system", lambda: "Windows")
    monkeypatch.setattr(android, "_adb", lambda: "adb")
    monkeypatch.setattr(android, "run", run)
    android_device.stop_screen_recording()
    run.assert_called_once_with(["taskkill", "/pid", "44"], capture_output=True)
    android.kill_server()
    assert run.call_args.args[0] == ["adb", "kill-server"]


def test_start_autoscroll_uses_default_dimensions(monkeypatch: pytest.MonkeyPatch, android_device) -> None:
    android_device.width = 0
    android_device.height = 0
    scroll = Mock()
    monkeypatch.setattr(android, "scroll", scroll)

    class OneShotEvent:
        def __init__(self) -> None:
            self.done = False

        def is_set(self) -> bool:
            return self.done

        def wait(self, timeout: float) -> None:
            self.done = True

    android_device.start_autoscroll("up", OneShotEvent())
    scroll.assert_called_once_with("android-1", "up", 1080, 1920)
