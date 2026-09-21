import json
import subprocess
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest

from app.devices import ios
from app.devices.devices import ConnectionType


@pytest.mark.parametrize(("version", "expected"), [("17", 170000), ("17.2", 170200), ("17.2.3", 170203)])
def test_version_to_int(version: str, expected: int) -> None:
    assert ios.version_to_int(version) == expected


def test_major_version() -> None:
    assert ios.major_version("16.7.2") == 16


def test_device_info_and_unsupported_operations(ios_device, tmp_path: Path) -> None:
    assert ios_device.get_info() == "iOS - iPhone (serial-1)"
    with pytest.raises(NotImplementedError):
        ios_device.backup(tmp_path)
    with pytest.raises(NotImplementedError):
        ios_device.extract_contacts(tmp_path / "contacts.txt")
    with pytest.raises(NotImplementedError):
        ios_device.extract_device_logs(tmp_path)


def test_get_device_info_handles_valid_and_invalid_json(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    run = Mock(side_effect=[completed_process('{"DeviceName": "Phone"}'), completed_process("invalid")])
    monkeypatch.setattr(ios, "run", run)
    assert ios.get_device_info("udid") == {"DeviceName": "Phone"}
    assert ios.get_device_info("udid") == {}


def test_get_connected_devices(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    monkeypatch.setattr(ios, "run", Mock(return_value=completed_process('{"deviceList": ["one", "two"]}')))
    monkeypatch.setattr(
        ios,
        "get_device_info",
        lambda udid: {
            "SerialNumber": f"serial-{udid}",
            "DeviceName": "Phone",
            "ProductVersion": "17.1",
            "ProductType": "unknown",
        },
    )
    monkeypatch.setattr(ios, "devmode_enabled", lambda udid: udid == "one")

    devices = ios.get_connected_devices()

    assert [device.connection_type for device in devices] == [ConnectionType.FULL, ConnectionType.PARTIAL]
    assert devices[0].serial == "serial-one"


def test_devmode_enabled(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    run = Mock(side_effect=[completed_process('{"DeveloperModeEnabled": true}'), completed_process("bad")])
    monkeypatch.setattr(ios, "run", run)
    assert ios.devmode_enabled("udid") is True
    assert ios.devmode_enabled("udid") is False


def test_enable_devmode_detects_passcode(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    monkeypatch.setattr(ios, "run", Mock(return_value=completed_process(stderr="Device has a passcode set")))
    with pytest.raises(ios.PasscodeEnabledError):
        ios.enable_devmode("udid")


def test_dev_image_mounted(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    stderr = json.dumps({"level": "info", "msg": "DeveloperDiskImage"})
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    monkeypatch.setattr(ios, "run", Mock(return_value=completed_process(stderr=stderr)))
    assert ios.dev_image_mounted("udid") is True


def test_screenshot_command(monkeypatch: pytest.MonkeyPatch, completed_process, tmp_path: Path) -> None:
    run = Mock(return_value=completed_process())
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    monkeypatch.setattr(ios, "run", run)
    output = tmp_path / "screens" / "a.png"
    assert ios.screenshot("udid", output) == output
    assert output.parent.is_dir()
    assert run.call_args.args[0][-1] == output


def test_extract_device_info(monkeypatch: pytest.MonkeyPatch, completed_process, ios_device, tmp_path: Path) -> None:
    run = Mock(
        side_effect=[
            completed_process("third.party"),
            completed_process("system.app"),
            completed_process('{"DeviceName": "Phone"}'),
        ]
    )
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    monkeypatch.setattr(ios, "run", run)
    ios_device.extract_device_info(tmp_path)
    assert (tmp_path / "installed_apps.txt").read_text() == "third.party"
    assert json.loads((tmp_path / "device_info.json").read_text()) == {"DeviceName": "Phone"}


def test_stop_recording_escalates_on_timeout(monkeypatch: pytest.MonkeyPatch, ios_device) -> None:
    process = Mock()
    process.wait.side_effect = subprocess.TimeoutExpired("uxplay", 3)
    ios_device.recording_process = process
    monkeypatch.setattr(ios.platform, "system", lambda: "Linux")
    ios_device.stop_screen_recording()
    process.terminate.assert_called_once()
    process.kill.assert_called_once()
    assert ios_device.recording_process is None


def test_tunnel_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    process = Mock()
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    monkeypatch.setattr(ios.platform, "system", lambda: "Windows")
    popen = Mock(return_value=process)
    monkeypatch.setattr(ios, "popen", popen)
    assert ios.start_ios_tunnel() is process
    ios.stop_ios_tunnel(process)
    process.terminate.assert_called_once()


def test_usbmuxd_available_when_service_active(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ios, "run", Mock(return_value=Mock(returncode=0)))
    monkeypatch.setattr(ios.platform, "system", lambda: "Linux")
    assert ios.usbmuxd_available() is True


def test_usbmuxd_unavailable_when_service_inactive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ios, "run", Mock(return_value=Mock(returncode=3)))
    monkeypatch.setattr(ios.platform, "system", lambda: "Linux")
    assert ios.usbmuxd_available() is False


def test_tunnel_skipped_when_usbmuxd_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ios, "run", Mock(return_value=Mock(returncode=3)))
    monkeypatch.setattr(ios.platform, "system", lambda: "Linux")
    popen = Mock()
    monkeypatch.setattr(ios, "popen", popen)
    assert ios.start_ios_tunnel() is None
    popen.assert_not_called()


def test_usbmuxd_check_is_skipped_outside_linux(monkeypatch: pytest.MonkeyPatch) -> None:
    run = Mock()
    monkeypatch.setattr(ios, "run", run)
    monkeypatch.setattr(ios.platform, "system", lambda: "Windows")
    assert ios.usbmuxd_available() is True
    run.assert_not_called()


def test_start_screen_recording_parses_status_and_moves_files(
    monkeypatch: pytest.MonkeyPatch, ios_device, fake_reporter, tmp_path: Path
) -> None:
    lines = [
        "An Open-Source AirPlay mirroring and audio-streaming server\n",
        "Initialized server socket\n",
        "CLIENT MUST NOW ENTER PIN\n",
        "Begin streaming to GStreamer video pipeline\n",
        "Stopped recording\n",
    ]
    process = Mock()
    process.stdout = iter(lines)
    process.stderr = iter(())
    process.terminate = Mock()
    monkeypatch.setattr(ios, "_uxplay", lambda: "uxplay")
    monkeypatch.setattr(ios.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(ios, "popen", Mock(return_value=process))
    temp_output = tmp_path / "recording.mp4"
    temp_output.write_bytes(b"video")
    destination = tmp_path / "destination" / "recording"

    ios_device.start_screen_recording(destination, fake_reporter)

    statuses = [call[1] for call in fake_reporter.status_changed.calls]
    assert statuses == [
        "Initialising UxPlay",
        "Waiting for connection",
        "UXPLAY_ENTER_PIN",
        "UXPLAY_STARTED_RECORDING",
        "Recording iOS device",
    ]
    process.terminate.assert_called_once()
    assert (destination.parent / "recording.mp4").read_bytes() == b"video"


def test_stop_recording_windows_graceful(monkeypatch: pytest.MonkeyPatch, completed_process, ios_device) -> None:
    process = Mock(pid=55)
    ios_device.recording_process = process
    run = Mock(return_value=completed_process())
    monkeypatch.setattr(ios.platform, "system", lambda: "Windows")
    monkeypatch.setattr(ios, "run", run)
    ios_device.stop_screen_recording()
    run.assert_called_once_with(["taskkill", "/pid", "55", "/T"], capture_output=True)
    process.wait.assert_called_once_with(timeout=3)
    assert ios_device.recording_process is None


def test_stop_recording_windows_forces_on_timeout(
    monkeypatch: pytest.MonkeyPatch, completed_process, ios_device
) -> None:
    process = Mock(pid=55)
    process.wait.side_effect = subprocess.TimeoutExpired("uxplay", 3)
    ios_device.recording_process = process
    run = Mock(return_value=completed_process())
    monkeypatch.setattr(ios.platform, "system", lambda: "Windows")
    monkeypatch.setattr(ios, "run", run)
    ios_device.stop_screen_recording()
    assert run.call_args_list[-1].args[0] == ["taskkill", "/f", "/pid", "55", "/T"]


def test_stop_recording_without_process(monkeypatch: pytest.MonkeyPatch, ios_device) -> None:
    run = Mock()
    monkeypatch.setattr(ios, "run", run)
    ios_device.stop_screen_recording()
    run.assert_not_called()


def test_mount_dev_image_and_scroll(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    run = Mock(return_value=completed_process())
    sleep = Mock()
    say = Mock()
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    monkeypatch.setattr(ios, "run", run)
    monkeypatch.setattr(ios.time, "sleep", sleep)
    monkeypatch.setattr(ios, "say", say)
    ios.mount_dev_image("udid")
    assert run.call_args.args[0] == ["ios", "image", "auto", "--udid", "udid"]
    sleep.assert_called_once_with(1)
    ios.scroll("left")
    say.assert_called_once_with("scroll left")


@pytest.mark.parametrize(
    "stderr",
    [
        "",
        json.dumps({"level": "warning", "msg": "image"}),
        json.dumps({"level": "info", "msg": "none"}),
    ],
)
def test_dev_image_not_mounted(monkeypatch: pytest.MonkeyPatch, completed_process, stderr: str) -> None:
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    monkeypatch.setattr(ios, "run", Mock(return_value=completed_process(stderr=stderr)))
    assert ios.dev_image_mounted("udid") is False


def test_enable_devmode_success(monkeypatch: pytest.MonkeyPatch, completed_process) -> None:
    run = Mock(return_value=completed_process(stderr=""))
    monkeypatch.setattr(ios, "_goios", lambda: "ios")
    monkeypatch.setattr(ios, "run", run)
    ios.enable_devmode("udid")
    assert "--enable-post-restart" in run.call_args.args[0]


def test_start_autoscroll_one_iteration(monkeypatch: pytest.MonkeyPatch, ios_device) -> None:
    scroll = Mock()
    monkeypatch.setattr(ios, "scroll", scroll)

    class OneShotEvent:
        def __init__(self) -> None:
            self.done = False

        def is_set(self) -> bool:
            return self.done

        def wait(self, timeout: float) -> None:
            self.done = True

    ios_device.start_autoscroll("right", OneShotEvent())
    scroll.assert_called_once_with("right")


def test_autoscroll_screenshot_detects_duplicate(monkeypatch: pytest.MonkeyPatch, ios_device, tmp_path: Path) -> None:
    screenshot_calls = 0

    def take_screenshot(udid: str, output: Path) -> Path:
        nonlocal screenshot_calls
        screenshot_calls += 1
        output.write_bytes(b"png")
        return output

    monkeypatch.setattr(ios, "screenshot", take_screenshot)
    monkeypatch.setattr(ios, "get_timestamp", lambda: "stamp")
    monkeypatch.setattr(ios.Image, "open", Mock(return_value=object()))
    monkeypatch.setattr(ios, "average_hash", Mock(side_effect=[10, 11]))
    monkeypatch.setattr(ios, "scroll", Mock())

    class NoWaitEvent:
        def is_set(self) -> bool:
            return False

        def wait(self, timeout: float) -> None:
            pass

    with pytest.raises(ios.DuplicateImageError):
        ios_device.autoscroll_screenshot(tmp_path, "down", NoWaitEvent())
    assert screenshot_calls == 2
    assert not (tmp_path / "screenshot_stamp.png").exists()


def test_autoscroll_screenshot_cancelled_before_capture(ios_device, tmp_path: Path) -> None:
    cancelled = threading.Event()
    cancelled.set()
    ios_device.autoscroll_screenshot(tmp_path, "down", cancelled)
    assert list(tmp_path.iterdir()) == []


def test_stop_tunnel_kills_after_timeout() -> None:
    process = Mock()
    process.wait.side_effect = subprocess.TimeoutExpired("ios", 3)
    ios.stop_ios_tunnel(process)
    process.kill.assert_called_once()
