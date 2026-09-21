from pathlib import Path
from typing import cast
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QObject, Signal

from app.controllers import devices_controller
from app.devices.devices import OperationType
from app.models.devices_model import DevicesModel
from app.views.devices_view import DevicesView


class FakeView(QObject):
    operation_requested = Signal(object, object)
    combo_operation_requested = Signal(object, object, str)
    cancel_requested = Signal(object)
    autoscroll_stop_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.update_devices = Mock()
        self.set_scanning = Mock()
        self.set_device_busy = Mock()
        self.set_status = Mock()
        self.set_progress = Mock()
        self.show_operation_waring = Mock()
        self.show_binary_choice = Mock(return_value=True)
        self._device_widget_map = {}


class FakeRunner(QObject):
    operation_started = Signal(str, object)
    operation_finished = Signal(str, object, object)
    operation_error = Signal(str, object, str)

    def __init__(self) -> None:
        super().__init__()
        self.submissions = []
        self.shutdown = Mock()

    def submit(self, device_id, operation_type, operation) -> None:
        self.submissions.append((device_id, operation_type, operation))


class FakeMonitor:
    def __init__(self) -> None:
        self.start_monitoring = Mock()
        self.stop_monitoring = Mock()


@pytest.fixture
def controller(monkeypatch: pytest.MonkeyPatch):
    runner = FakeRunner()
    monitor = FakeMonitor()
    tunnel = Mock()
    tunnel.poll.return_value = None
    monkeypatch.setattr(devices_controller, "DeviceOperationRunner", lambda: runner)
    monkeypatch.setattr(devices_controller, "USBMonitor", lambda: monitor)
    monkeypatch.setattr(devices_controller.ios, "usbmuxd_available", Mock(return_value=True))
    monkeypatch.setattr(devices_controller.ios, "start_ios_tunnel", Mock(return_value=tunnel))
    view = FakeView()
    model = DevicesModel()
    instance = devices_controller.DevicesController(cast(DevicesView, cast(object, view)), model)
    return instance, view, model, runner, monitor, tunnel


def test_tunnel_waits_for_usbmuxd(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FakeRunner()
    monitor = FakeMonitor()
    tunnel = Mock()
    tunnel.poll.return_value = None
    start_tunnel = Mock(return_value=tunnel)
    monkeypatch.setattr(devices_controller, "DeviceOperationRunner", lambda: runner)
    monkeypatch.setattr(devices_controller, "USBMonitor", lambda: monitor)
    monkeypatch.setattr(devices_controller.ios, "start_ios_tunnel", start_tunnel)
    usbmuxd_available = Mock(side_effect=[False, False, True])
    monkeypatch.setattr(devices_controller.ios, "usbmuxd_available", usbmuxd_available)
    monkeypatch.setattr(devices_controller.android, "get_connected_devices", Mock(return_value=[]))
    monkeypatch.setattr(devices_controller.ios, "get_connected_devices", Mock(return_value=[]))
    view = FakeView()

    instance = devices_controller.DevicesController(
        cast(DevicesView, cast(object, view)),
        DevicesModel(),
    )

    view.show_operation_waring.assert_not_called()
    start_tunnel.assert_not_called()

    instance.start_scan()
    runner.submissions[-1][2]()
    view.show_operation_waring.assert_not_called()
    start_tunnel.assert_not_called()

    instance.start_scan()
    runner.submissions[-1][2]()
    start_tunnel.assert_called_once()
    assert instance._go_ios_tunnel_proc is tunnel


def test_shutdown_without_ios_tunnel(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = FakeRunner()
    monitor = FakeMonitor()
    monkeypatch.setattr(devices_controller, "DeviceOperationRunner", lambda: runner)
    monkeypatch.setattr(devices_controller, "USBMonitor", lambda: monitor)
    monkeypatch.setattr(devices_controller.ios, "usbmuxd_available", Mock(return_value=False))
    stop_tunnel = Mock()
    kill_server = Mock()
    monkeypatch.setattr(devices_controller.ios, "stop_ios_tunnel", stop_tunnel)
    monkeypatch.setattr(devices_controller.android, "kill_server", kill_server)
    view = FakeView()
    instance = devices_controller.DevicesController(
        cast(DevicesView, cast(object, view)),
        DevicesModel(),
    )

    instance.shutdown()

    stop_tunnel.assert_not_called()
    kill_server.assert_called_once()
    runner.shutdown.assert_called_once()


def test_scan_combines_platform_devices(
    controller, monkeypatch: pytest.MonkeyPatch, android_device, ios_device
) -> None:
    instance, _, _, runner, _, _ = controller
    monkeypatch.setattr(devices_controller.android, "get_connected_devices", lambda: [android_device])
    monkeypatch.setattr(devices_controller.ios, "get_connected_devices", lambda: [ios_device])

    instance.start_scan()

    _, operation_type, operation = runner.submissions[-1]
    assert operation_type is OperationType.DEVICE_SCAN
    assert operation() == [android_device, ios_device]


def test_scan_lifecycle_updates_view_and_model(controller, android_device) -> None:
    instance, view, model, _, _, _ = controller
    instance._on_operation_started("", OperationType.DEVICE_SCAN)
    view.set_scanning.assert_called_once_with(True)

    instance._on_operation_finished("", OperationType.DEVICE_SCAN, [android_device])

    view.set_scanning.assert_called_with(False)
    assert model.devices == [android_device]


def test_generate_output_directory(controller, android_device, tmp_path: Path) -> None:
    instance, _, model, _, _, _ = controller
    model.output_directory = tmp_path
    assert instance._generate_output_directory(android_device) == tmp_path / "android-1"
    model.job_number = "JOB-1"
    android_device.exhibit_id = "EX-2"
    assert instance._generate_output_directory(android_device) == tmp_path / "JOB-1" / "EX-2_android-1"


def test_screenshot_submission(controller, monkeypatch: pytest.MonkeyPatch, android_device, tmp_path: Path) -> None:
    instance, view, model, runner, _, _ = controller
    model.output_directory = tmp_path
    monkeypatch.setattr(devices_controller, "get_timestamp", lambda: "20260101_010101")
    screenshot = Mock(return_value=tmp_path / "screen.png")
    android_device.screenshot = screenshot

    instance._on_screenshot_requested(android_device)

    device_id, operation_type, operation = runner.submissions[-1]
    assert device_id == "android-1"
    assert operation_type is OperationType.SCREENSHOT
    operation()
    screenshot.assert_called_once_with(
        (tmp_path / "android-1" / "screenshots" / "screenshot_20260101_010101.png").resolve()
    )
    view.set_status.assert_called_with("android-1", "Taking screenshot")


def test_ios_screenshot_mount_confirmation_declined(controller, monkeypatch: pytest.MonkeyPatch, ios_device) -> None:
    instance, view, _, runner, _, _ = controller
    ios_device.os_version = "16.6"
    monkeypatch.setattr(devices_controller.ios, "dev_image_mounted", lambda *args: False)
    view.show_binary_choice.return_value = False

    instance._on_screenshot_requested(ios_device)

    assert runner.submissions == []
    view.set_device_busy.assert_called_with("ios-1", OperationType.IDLE)


def test_operation_failure_warns_and_resets(controller) -> None:
    instance, view, _, _, _, _ = controller
    instance._on_operation_failed("device", OperationType.BACKUP, "failed")
    view.set_device_busy.assert_called_with("device", OperationType.IDLE)
    view.show_operation_waring.assert_called_with("BACKUP failed", "failed")


def test_usb_scan_is_deferred(controller) -> None:
    instance, _, _, _, _, _ = controller
    instance._usb_scan_timer = Mock()

    instance._schedule_usb_scan(True)
    assert instance._pending_usb_connect
    instance._usb_scan_timer.start.assert_called_once_with(2000)

    instance._schedule_usb_scan(False)
    instance._usb_scan_timer.start.assert_called_with(500)


def test_cancel_stops_recording(controller, android_device) -> None:
    instance, _, _, _, _, _ = controller
    android_device.recording_process = Mock()
    android_device.stop_screen_recording = Mock()
    instance._on_cancel_requested(android_device)
    android_device.stop_screen_recording.assert_called_once()


def test_shutdown_releases_resources(controller, monkeypatch: pytest.MonkeyPatch, android_device) -> None:
    instance, _, model, runner, monitor, tunnel = controller
    process = Mock()
    android_device.recording_process = process
    model.devices = [android_device]
    kill_server = Mock()
    stop_tunnel = Mock()
    monkeypatch.setattr(devices_controller.android, "kill_server", kill_server)
    monkeypatch.setattr(devices_controller.ios, "stop_ios_tunnel", stop_tunnel)

    instance.shutdown()

    monitor.stop_monitoring.assert_called_once()
    kill_server.assert_called_once()
    process.kill.assert_called_once()
    stop_tunnel.assert_called_once_with(tunnel)
    runner.shutdown.assert_called_once()


@pytest.mark.parametrize(
    ("operation", "handler"),
    [
        (OperationType.ENABLE_DEV_MODE, "_on_enable_devmode_requested"),
        (OperationType.BACKUP, "_on_backup_requested"),
        (OperationType.EXTRACT_CONTACTS, "_on_contacts_extraction_requested"),
        (OperationType.EXTRACT_DEVICE_INFO, "_on_device_info_extraction_requested"),
        (OperationType.EXTRACT_DEVICE_LOGS, "_on_device_logs_extraction_requested"),
        (OperationType.SCREEN_RECORDING, "_on_screen_recording_requested"),
        (OperationType.SCREENSHOT, "_on_screenshot_requested"),
    ],
)
def test_operation_request_routes(controller, android_device, operation, handler: str) -> None:
    instance, _, _, _, _, _ = controller
    callback = Mock()
    setattr(instance, handler, callback)
    instance._on_operation_requested(operation, android_device)
    callback.assert_called_once_with(android_device)


@pytest.mark.parametrize(
    ("operation", "expected"),
    [
        (OperationType.AUTOSCROLL, OperationType.STOP_AUTOSCROLL),
        (OperationType.SCREEN_RECORDING, OperationType.STOP_SCREEN_RECORDING),
        (OperationType.AUTOSCROLL_SCREENSHOT, OperationType.STOP_AUTOSCROLL_SCREENSHOT),
        (OperationType.BACKUP, OperationType.IDLE),
    ],
)
def test_operation_finished_states(controller, operation, expected) -> None:
    instance, view, _, _, _, _ = controller
    instance._on_operation_finished("device", operation, None)
    view.set_device_busy.assert_called_with("device", expected)


def test_developer_mode_finish_starts_scan(controller) -> None:
    instance, _, _, _, _, _ = controller
    instance.start_scan = Mock()
    instance._on_operation_finished("device", OperationType.ENABLE_DEV_MODE, None)
    instance.start_scan.assert_called_once()


def test_non_scan_operation_started_marks_busy(controller) -> None:
    instance, view, _, _, _, _ = controller
    instance._on_operation_started("device", OperationType.BACKUP)
    view.set_device_busy.assert_called_once_with("device", OperationType.BACKUP)


def test_backup_submission_reuses_event(
    controller, monkeypatch: pytest.MonkeyPatch, android_device, tmp_path: Path
) -> None:
    instance, _, model, runner, _, _ = controller
    model.output_directory = tmp_path
    monkeypatch.setattr(devices_controller, "get_timestamp", lambda: "stamp")
    backup = Mock(return_value=tmp_path)
    android_device.backup = backup
    instance._on_backup_requested(android_device)
    event = instance._cancel_events[android_device.identifier]
    event.set()
    instance._on_backup_requested(android_device)
    assert not event.is_set()
    _, operation, callback = runner.submissions[-1]
    assert operation is OperationType.BACKUP
    callback()
    assert backup.call_args.args[0] == (tmp_path / "android-1" / "backups" / "backup_stamp").resolve()
    assert backup.call_args.args[2] is event


@pytest.mark.parametrize(
    ("request_method", "operation", "method", "folder"),
    [
        ("_on_contacts_extraction_requested", OperationType.EXTRACT_CONTACTS, "extract_contacts", "contacts_stamp.txt"),
        (
            "_on_device_info_extraction_requested",
            OperationType.EXTRACT_DEVICE_INFO,
            "extract_device_info",
            "device_info_stamp",
        ),
        (
            "_on_device_logs_extraction_requested",
            OperationType.EXTRACT_DEVICE_LOGS,
            "extract_device_logs",
            "device_logs_stamp",
        ),
    ],
)
def test_extraction_submissions(
    controller,
    monkeypatch: pytest.MonkeyPatch,
    android_device,
    tmp_path: Path,
    request_method: str,
    operation,
    method: str,
    folder: str,
) -> None:
    instance, _, model, runner, _, _ = controller
    model.output_directory = tmp_path
    monkeypatch.setattr(devices_controller, "get_timestamp", lambda: "stamp")
    device_method = Mock()
    setattr(android_device, method, device_method)
    getattr(instance, request_method)(android_device)
    _, submitted_type, callback = runner.submissions[-1]
    assert submitted_type is operation
    callback()
    assert device_method.call_args.args[0] == (tmp_path / "android-1" / folder).resolve()


@pytest.mark.parametrize(("os_name", "suffix"), [("Android", "recording_stamp.mp4"), ("iOS", "recording_stamp")])
def test_recording_submission(
    controller, monkeypatch: pytest.MonkeyPatch, android_device, tmp_path: Path, os_name: str, suffix: str
) -> None:
    instance, _, model, runner, _, _ = controller
    model.output_directory = tmp_path
    android_device.os = os_name
    monkeypatch.setattr(devices_controller, "get_timestamp", lambda: "stamp")
    record = Mock()
    android_device.start_screen_recording = record
    instance._on_screen_recording_requested(android_device)
    _, operation, callback = runner.submissions[-1]
    assert operation is OperationType.SCREEN_RECORDING
    callback()
    assert record.call_args.args[0] == (tmp_path / "android-1" / "recordings" / suffix).resolve()


def test_ios_image_decisions(controller, monkeypatch: pytest.MonkeyPatch, ios_device, android_device) -> None:
    instance, _, _, _, _, _ = controller
    monkeypatch.setattr(devices_controller.ios, "dev_image_mounted", lambda *args: False)
    ios_device.os_version = "16.7"
    assert instance._ios_needs_dev_image(ios_device) is True
    ios_device.os_version = "17.0"
    assert instance._ios_needs_dev_image(ios_device) is False
    assert instance._ios_needs_dev_image(android_device) is False
    ios_device.os_version = "16.7"
    monkeypatch.setattr(devices_controller.ios, "dev_image_mounted", lambda *args: True)
    assert instance._ios_needs_dev_image(ios_device) is False


def test_autoscroll_submission_and_stop(controller, ios_device) -> None:
    instance, view, _, runner, _, _ = controller
    start = Mock()
    ios_device.start_autoscroll = start
    instance._on_autoscroll_requested(ios_device, "down")
    view.show_operation_waring.assert_called_once()
    _, operation, callback = runner.submissions[-1]
    assert operation is OperationType.AUTOSCROLL
    callback()
    event = instance._autoscroll_events[ios_device.identifier]
    start.assert_called_once()
    instance._on_autoscroll_stop_requested(ios_device)
    assert event.is_set()


def test_enable_devmode_declined_and_accepted(controller, monkeypatch: pytest.MonkeyPatch, ios_device) -> None:
    instance, view, _, runner, _, _ = controller
    view.show_binary_choice.return_value = False
    instance._on_enable_devmode_requested(ios_device)
    assert runner.submissions == []
    view.set_device_busy.assert_called_with("ios-1", OperationType.IDLE)
    view.show_binary_choice.return_value = True
    ios_device.os_version = "16.5"
    enable = Mock()
    mount = Mock()
    monkeypatch.setattr(devices_controller.ios, "enable_devmode", enable)
    monkeypatch.setattr(devices_controller.ios, "dev_image_mounted", lambda *args: False)
    monkeypatch.setattr(devices_controller.ios, "mount_dev_image", mount)
    instance._on_enable_devmode_requested(ios_device)
    runner.submissions[-1][2]()
    enable.assert_called_once_with("ios-1")
    mount.assert_called_once_with("ios-1")


def test_usb_callbacks_emit_events(controller) -> None:
    instance, _, _, _, _, _ = controller
    spy = Mock()
    instance.usb_event.connect(spy)
    instance._on_usb_connect("id", {})
    instance._on_usb_disconnect("id", {})
    assert [call.args for call in spy.call_args_list] == [(True,), (False,)]
