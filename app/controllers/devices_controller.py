from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal, Slot

from app.devices import android, ios
from app.devices.devices import Device
from app.models.devices_model import DevicesModel
from app.utils.event_bus import EventBus
from app.utils.generic import get_timestamp
from app.views.devices_view import DevicesView


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


class DevicesController(QObject):
    def __init__(self, view: DevicesView, model: DevicesModel) -> None:
        super().__init__()

        self._view = view
        self._model = model

        self._output_directory: str = ""
        self._job_number: str = ""

        self._runner = DeviceOperationRunner()

        self._view.screenshot_requested.connect(self._on_screenshot_requested)
        self._view.backup_requested.connect(self._on_backup_requested)

        # Wire model to view
        self._model.devices_changed.connect(
            lambda: self._view.update_devices(self._model.devices)
        )

        # Subscribe to event bus for operation events
        self._runner.operation_started.connect(self._on_operation_started)
        self._runner.operation_finished.connect(self._on_operation_finished)
        self._runner.operation_error.connect(self._on_operation_failed)

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

    @Slot(str, str)
    def _on_operation_started(self, device_id: str, operation_type: str) -> None:
        """Handle operation started from ConnectedDevicesController."""
        logger.info(f"Started operation {operation_type} for device {device_id}")
        self._view.set_device_busy(device_id, True)

    @Slot(str, str, object)
    def _on_operation_finished(
        self, device_id: str, operation_type: str, result: object
    ) -> None:
        """Handle operation finished from ConnectedDevicesController."""
        self._view.set_device_busy(device_id, False)

        # Special handling for device scan - update model with device list
        if operation_type == "device_scan":
            devices = result if isinstance(result, list) else []
            logger.info(f"DevicesController received {len(devices)} devices from scan")
            self._model.set_devices(devices)
            self._view.update_devices(self._model.devices)

    @Slot(str, str, str)
    def _on_operation_failed(
        self, device_id: str, operation_type: str, error: str
    ) -> None:
        """Handle operation failed from ConnectedDevicesController."""
        self._view.set_device_busy(device_id, False)
        self._view.show_operation_failed_warning(
            f"{operation_type.capitalize()} failed", error
        )

    # @Slot(Device)
    # def _on_screenshot_requested(self, device: Device) -> None:
    #     """Handle screenshot request for a device and emit signal."""
    #     logger.info(f"Screenshot requested for {device.os} device: {device.identifier}")
    #     self._event_bus.screenshot_requested.emit(device)

    @Slot(Device)
    def _on_screenshot_requested(self, device: Device) -> None:
        """Take a screenshot of the specified device."""
        logger.debug(f"Taking screenshot of {device.os} device: {device.serial}")
        output_file = Path(self._output_directory) / f"screenshot_{get_timestamp()}.png"

        def screenshot_operation() -> Path:
            return device.screenshot(output_file)

        self._runner.submit(device.identifier, "screenshot", screenshot_operation)

    # @Slot(Device)
    # def _on_backup_requested(self, device: Device) -> None:
    #     logger.info(f"Backup requested for {device.os} device: {device.identifier}")
    #     self._event_bus.backup_requested.emit(device)

    @Slot(Device)
    def _on_backup_requested(self, device: Device) -> None:
        """Take a backup of the specified device."""
        logger.debug(f"Taking backup of {device.os} device: {device.identifier}")
        output_file = Path(self._output_directory) / f"backup_{get_timestamp()}.ab"

        def backup_operation() -> Path:
            return device.backup(output_file)

        self._runner.submit(device.identifier, "backup", backup_operation)
