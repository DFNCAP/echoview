import subprocess
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal, Slot

from app.devices import android, ios
from app.devices.devices import Device, OperationType, StatusReporter
from app.models.devices_model import DevicesModel
from app.utils.generic import get_timestamp
from app.views.devices_view import DevicesView


class DeviceOperationRunner(QObject):
    operation_started = Signal(str, OperationType)
    operation_finished = Signal(str, OperationType, object)
    operation_error = Signal(str, OperationType, str)

    def __init__(self) -> None:
        super().__init__()
        self._executor = ThreadPoolExecutor()

    def submit(
        self,
        device_id: str,
        operation_type: OperationType,
        operation: Callable[..., object],
    ) -> None:
        self._executor.submit(self._run, device_id, operation_type, operation)

    def _run(
        self,
        device_id: str,
        operation_type: OperationType,
        operation: Callable[..., object],
    ) -> None:

        self.operation_started.emit(device_id, operation_type)
        try:
            result = operation()
            self.operation_finished.emit(device_id, operation_type, result)
        except Exception as e:
            self.operation_error.emit(device_id, operation_type, str(e))

    def shutdown(self) -> None:
        android.kill_server()
        self._executor.shutdown(wait=False, cancel_futures=True)


class DevicesController(QObject):
    def __init__(self, view: DevicesView, model: DevicesModel) -> None:
        super().__init__()

        self._view = view
        self._model = model

        self._job_number: str = ""

        self._cancel_events: dict[str, threading.Event] = {}
        self._autoscroll_events: dict[str, threading.Event] = {}

        self._runner = DeviceOperationRunner()
        self._cancelled = threading.Event()
        self._go_ios_tunnel_proc: subprocess.Popen[bytes] | None = ios.start_ios_tunnel()

        self._view.operation_requested.connect(self._on_operation_requested)

        self._view.cancel_requested.connect(self._on_cancel_requested)
        self._view.autoscroll_stop_requested.connect(self._on_autoscroll_stop_requested)

        # Wire model to view
        self._model.devices_changed.connect(self._view.update_devices)

        # Subscribe to event bus for operation events
        self._runner.operation_started.connect(self._on_operation_started)
        self._runner.operation_finished.connect(self._on_operation_finished)
        self._runner.operation_error.connect(self._on_operation_failed)

        # Track running operations per device
        self._device_operations: dict[str, set[OperationType]] = {}

    @Slot(Path)
    def set_output_directory(self, directory: Path) -> None:
        self._model.output_directory = directory

    @Slot(str)
    def set_job_number(self, job_number: str) -> None:
        self._model.job_number = job_number

    @Slot()
    def start_scan(self) -> None:
        logger.debug("Starting device scan")

        def scan_operation() -> list[Device]:
            devices: list[Device] = []
            android_devices = android.get_connected_devices()
            if android_devices:
                devices.extend(android_devices)

            ios_devices = ios.get_connected_devices()
            if ios_devices:
                devices.extend(ios_devices)

            return devices

        self._runner.submit("", OperationType.DEVICE_SCAN, scan_operation)

    @Slot(str, int)
    def _on_operation_started(self, device_id: str, operation_type: OperationType) -> None:
        logger.info(f"Started operation {operation_type.name} for device {device_id}")
        # Show scanning indicator for device scan
        if operation_type == OperationType.DEVICE_SCAN:
            self._view.set_scanning(True)

        # Track this operation for the device
        if device_id not in self._device_operations:
            self._device_operations[device_id] = set()
        self._device_operations[device_id].add(operation_type)

        self._view.set_device_busy(device_id, operation_type)

    @Slot(str, str, object)
    def _on_operation_finished(self, device_id: str, operation_type: OperationType, result: object) -> None:
        logger.info(f"Finished operation {operation_type.name} for device {device_id}")

        # Remove this operation from tracking
        if device_id in self._device_operations:
            self._device_operations[device_id].discard(operation_type)

        # Special signal for autoscroll finishing (to coordinate with screen recording)
        if operation_type == OperationType.AUTOSCROLL:
            self._view.set_device_autoscroll_finished(device_id)
            if OperationType.SCREEN_RECORDING not in self._device_operations.get(device_id, set()):
                self._view.set_device_busy(device_id, OperationType.IDLE)
        elif operation_type == OperationType.SCREEN_RECORDING:
            has_autoscroll = OperationType.AUTOSCROLL in self._device_operations.get(device_id, set())
            if has_autoscroll:
                self._view.set_device_recording_finished(device_id)
            else:
                self._view.set_device_busy(device_id, OperationType.IDLE)
        elif operation_type == OperationType.DEVICE_SCAN:
            self._view.set_scanning(False)
            devices = result if isinstance(result, list) else []
            logger.info(f"DevicesController received {len(devices)} devices from scan")
            self._model.devices = devices
        else:
            self._view.set_device_busy(device_id, OperationType.IDLE)

        if operation_type == OperationType.ENABLE_DEV_MODE:
            self.start_scan()

    @Slot(str, str, str)
    def _on_operation_failed(self, device_id: str, operation_type: OperationType, error: str) -> None:
        logger.warning(f"Error during operation {operation_type.name} for device {device_id}")

        # Remove this operation from tracking
        if device_id in self._device_operations:
            self._device_operations[device_id].discard(operation_type)

        # Hide scanning indicator if device scan fails
        if operation_type == OperationType.DEVICE_SCAN:
            self._view.set_scanning(False)
        elif operation_type == OperationType.AUTOSCROLL:
            self._view.set_device_autoscroll_finished(device_id)
            if OperationType.SCREEN_RECORDING not in self._device_operations.get(device_id, set()):
                self._view.set_device_busy(device_id, OperationType.IDLE)
        elif operation_type == OperationType.SCREEN_RECORDING:
            has_autoscroll = OperationType.AUTOSCROLL in self._device_operations.get(device_id, set())
            if has_autoscroll:
                self._view.set_device_recording_finished(device_id)
            else:
                self._view.set_device_busy(device_id, OperationType.IDLE)
        else:
            self._view.set_device_busy(device_id, OperationType.IDLE)

        self._view.show_operation_waring(f"{operation_type.name} failed", error)

    @Slot(OperationType, Device)
    def _on_operation_requested(self, operation: OperationType, device: Device) -> None:
        match operation:
            case OperationType.ENABLE_DEV_MODE:
                self._on_enable_devmode_requested(device)
            case OperationType.BACKUP:
                self._on_backup_requested(device)
            case OperationType.EXTRACT_CONTACTS:
                self._on_contacts_extraction_requested(device)
            case OperationType.EXTRACT_DEVICE_INFO:
                self._on_device_info_extraction_requested(device)
            case OperationType.EXTRACT_DEVICE_LOGS:
                self._on_device_logs_extraction_requested(device)
            case OperationType.SCREEN_RECORDING:
                self._on_screen_recording_requested(device)
            case OperationType.AUTOSCROLL_UP:
                self._on_autoscroll_requested(device, "up")
            case OperationType.AUTOSCROLL_DOWN:
                self._on_autoscroll_requested(device, "down")
            case OperationType.AUTOSCROLL_LEFT:
                self._on_autoscroll_requested(device, "left")
            case OperationType.AUTOSCROLL_RIGHT:
                self._on_autoscroll_requested(device, "right")
            case OperationType.AUTOSCROLL_SCREENSHOT_UP:
                self._on_autoscroll_screenshot_requested(device, "up")
            case OperationType.AUTOSCROLL_SCREENSHOT_DOWN:
                self._on_autoscroll_screenshot_requested(device, "down")
            case OperationType.AUTOSCROLL_SCREENSHOT_LEFT:
                self._on_autoscroll_screenshot_requested(device, "left")
            case OperationType.AUTOSCROLL_SCREENSHOT_RIGHT:
                self._on_autoscroll_screenshot_requested(device, "right")
            case OperationType.SCREENSHOT:
                self._on_screenshot_requested(device)

    @Slot(Device)
    def _on_backup_requested(self, device: Device) -> None:
        """Take a backup of the specified device."""
        logger.debug(f"Taking backup of {device.os} device: {device.identifier}")
        output_file = (
            self._model.output_directory
            / (self._model.job_number or device.identifier)
            / "backups"
            / f"backup_{get_timestamp()}"
        )

        reporter = StatusReporter()
        widget = self._view._device_widget_map.get(device.identifier)
        if widget:
            reporter.status_changed.connect(widget.set_status)
            reporter.progress_changed.connect(widget.set_progress)

        if device.identifier not in self._cancel_events:
            self._cancel_events[device.identifier] = threading.Event()
        else:
            self._cancel_events[device.identifier].clear()

        def backup_operation() -> Path:
            return device.backup(output_file.resolve(), reporter, self._cancel_events[device.identifier])

        if self._view.show_binary_choice(
            title="Device Backup",
            text="Device Backup",
            information="This operation may take a long time to complete. Proceed?",
        ):
            self._runner.submit(device.identifier, OperationType.BACKUP, backup_operation)
        else:
            logger.info("Setting device not busy")
            self._view.set_device_busy(device.identifier, OperationType.IDLE)

    @Slot(Device)
    def _on_contacts_extraction_requested(self, device: Device) -> None:
        output_file = (
            self._model.output_directory
            / (self._model.job_number or device.identifier)
            / f"contacts_{get_timestamp()}.txt"
        )

        def extract_contacts_operation() -> Path:
            return device.extract_contacts(output_file.resolve())

        self._runner.submit(
            device.identifier,
            OperationType.EXTRACT_CONTACTS,
            extract_contacts_operation,
        )

    @Slot(Device)
    def _on_device_logs_extraction_requested(self, device: Device) -> None:
        output_file = (
            self._model.output_directory
            / (self._model.job_number or device.identifier)
            / f"device_logs_{get_timestamp()}.txt"
        )

        reporter = StatusReporter()
        widget = self._view._device_widget_map.get(device.identifier)
        if widget:
            reporter.status_changed.connect(widget.set_status)
            reporter.progress_changed.connect(widget.set_progress)

        if device.identifier not in self._cancel_events:
            self._cancel_events[device.identifier] = threading.Event()
        else:
            self._cancel_events[device.identifier].clear()

        def extract_device_logs_operation() -> None:
            return device.extract_device_logs(output_file.resolve(), reporter, self._cancel_events[device.identifier])

        self._runner.submit(
            device.identifier,
            OperationType.EXTRACT_DEVICE_LOGS,
            extract_device_logs_operation,
        )

    @Slot(Device)
    def _on_device_info_extraction_requested(self, device: Device) -> None:
        output_directory = (
            self._model.output_directory
            / (self._model.job_number or device.identifier)
            / f"device_info_{get_timestamp()}.txt"
        )

        def extract_device_info_operation() -> None:
            return device.extract_device_info(output_directory.resolve())

        self._runner.submit(
            device.identifier,
            OperationType.EXTRACT_DEVICE_INFO,
            extract_device_info_operation,
        )

    @Slot(Device)
    def _on_screen_recording_requested(self, device: Device) -> None:
        output_file = (
            self._model.output_directory
            / (self._model.job_number or device.identifier)
            / "recordings"
            / f"recording_{get_timestamp()}.mp4"
        )
        reporter = None
        if device.os == "iOS":
            reporter = StatusReporter()
            widget = self._view._device_widget_map.get(device.identifier)
            if widget and reporter:
                reporter.status_changed.connect(widget.set_status)

        def screen_recording_operation() -> None:
            return device.start_screen_recording(output_file.resolve(), reporter)

        self._runner.submit(
            device.identifier,
            OperationType.SCREEN_RECORDING,
            screen_recording_operation,
        )

    @Slot(Device)
    def _on_screenshot_requested(self, device: Device) -> None:
        """Take a screenshot of the specified device."""

        output_file = (
            self._model.output_directory
            / (self._model.job_number or device.identifier)
            / "screenshots"
            / f"screenshot_{get_timestamp()}.png"
        )

        def screenshot_operation() -> Path:
            return device.screenshot(output_file.resolve())

        self._runner.submit(device.identifier, OperationType.SCREENSHOT, screenshot_operation)

    @Slot(Device)
    def _on_cancel_requested(self, device: Device) -> None:

        if device.identifier in self._cancel_events:
            self._cancel_events[device.identifier].set()

        if device.identifier in self._autoscroll_events:
            self._autoscroll_events[device.identifier].set()

        if device.recording_process:
            if device.os == "iOS":
                self._view.show_operation_waring(
                    "Stop Recording",
                    "Please ensure you have stopped screen mirroring on the device before proceeding to avoid video corruption",
                )
            device.stop_screen_recording()

        widget = self._view._device_widget_map.get(device.identifier)
        if widget:
            widget.set_status("Cancelling current operation, please wait")

    @Slot(Device, str)
    def _on_autoscroll_requested(self, device: Device, direction: str) -> None:
        # Create or reset autoscroll event
        if device.identifier not in self._autoscroll_events:
            self._autoscroll_events[device.identifier] = threading.Event()
        else:
            self._autoscroll_events[device.identifier].clear()

        def autoscroll_operation() -> None:
            device.start_autoscroll(direction, self._autoscroll_events[device.identifier])

        self._runner.submit(device.identifier, OperationType.AUTOSCROLL, autoscroll_operation)

    @Slot(Device)
    def _on_autoscroll_stop_requested(self, device: Device) -> None:
        if device.identifier in self._autoscroll_events:
            self._autoscroll_events[device.identifier].set()

    @Slot(Device, str)
    def _on_autoscroll_screenshot_requested(self, device: Device, direction: str) -> None:
        output_directory = (
            self._model.output_directory
            / (self._model.job_number or device.identifier)
            / f"autoscroll_screenshots_{get_timestamp()}"
        )

        # Create or reset autoscroll screenshot event
        if device.identifier not in self._autoscroll_events:
            self._autoscroll_events[device.identifier] = threading.Event()
        else:
            self._autoscroll_events[device.identifier].clear()

        def autoscroll_screenshot_operation() -> None:
            device.autoscroll_screenshot(
                output_directory.resolve(),
                direction,
                self._autoscroll_events[device.identifier],
            )

        self._runner.submit(
            device.identifier,
            OperationType.AUTOSCROLL_SCREENSHOT,
            autoscroll_screenshot_operation,
        )

    def _on_enable_devmode_requested(self, device: Device) -> None:

        self._runner.submit(
            device.identifier, OperationType.ENABLE_DEV_MODE, lambda: ios.enable_devmode(device.identifier)
        )

    def shutdown(self) -> None:
        # Kill all pending tasks before shutting down
        for _, event in self._cancel_events.items():
            event.set()

        # Stop all autoscroll operations
        for _, event in self._autoscroll_events.items():
            event.set()

        # Forcefully terminate all recording processes
        for device in self._model.devices:
            if device.recording_process:
                device.recording_process.kill()
                device.recording_process = None

        if self._go_ios_tunnel_proc:
            ios.stop_ios_tunnel(self._go_ios_tunnel_proc)
            self._go_ios_tunnel_proc = None

        self._runner.shutdown()
