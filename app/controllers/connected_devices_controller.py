from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal, Slot

from app.devices import android, ios
from app.devices.devices import Device
from app.utils.event_bus import EventBus
from app.utils.generic import get_timestamp


class DeviceOperationRunner(QObject):
    operation_started = Signal(str, str)  # device_id, operation_type
    operation_finished = Signal(str, str, object)  # device_id, operation_type, result
    operation_error = Signal(str, str, str)  # device_id, operation_type, error_message

    def __init__(self, max_workers: int = 4) -> None:
        super().__init__()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(
        self, device_id: str, operation_type: str, operation: Callable[..., object]
    ) -> None:
        self._executor.submit(self._run, device_id, operation_type, operation)

    def _run(
        self, device_id: str, operation_type: str, operation: Callable[..., object]
    ) -> None:
        self.operation_started.emit(device_id, operation_type)
        try:
            result = operation()
            self.operation_finished.emit(device_id, operation_type, result)
        except Exception as e:
            self.operation_error.emit(device_id, operation_type, str(e))

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


class ConnectedDevicesController(QObject):
    """Controller for managing device scanning and operations."""

    def __init__(self, event_bus: EventBus) -> None:
        super().__init__()
        self._event_bus = event_bus
        self._output_directory: str = ""
        self._job_number: str = ""

        self._runner = DeviceOperationRunner()

        # Wire runner signals to event bus
        self._runner.operation_started.connect(self._event_bus.operation_started.emit)
        self._runner.operation_finished.connect(self._event_bus.operation_finished.emit)
        self._runner.operation_error.connect(self._event_bus.operation_error.emit)

        # Subscribe to event bus for requests
        self._event_bus.screenshot_requested.connect(self.take_screenshot)
        self._event_bus.backup_requested.connect(self.backup)

    @Slot(str)
    def set_output_directory(self, directory: str) -> None:
        self._output_directory = directory

    @Slot(str)
    def set_job_number(self, job_number: str) -> None:
        self._job_number = job_number

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

        self._runner.submit("", "device_scan", scan_operation)

    @Slot(object)
    def take_screenshot(self, device: Device) -> None:
        """Take a screenshot of the specified device."""
        logger.debug(f"Taking screenshot of {device.os} device: {device.serial}")
        output_file = Path(self._output_directory) / f"screenshot_{get_timestamp()}.png"

        def screenshot_operation() -> Path:
            return device.screenshot(output_file)

        self._runner.submit(device.identifier, "screenshot", screenshot_operation)

    @Slot(object)
    def backup(self, device: Device) -> None:
        """Take a backup of the specified device."""
        logger.debug(f"Taking backup of {device.os} device: {device.identifier}")
        output_file = Path(self._output_directory) / f"backup_{get_timestamp()}.ab"

        def backup_operation() -> Path:
            return device.backup(output_file)

        self._runner.submit(device.identifier, "backup", backup_operation)
