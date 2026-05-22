from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, QThread, Signal, Slot

from app.devices.android import get_connected_devices as get_android_devices
from app.devices.devices import Device
from app.devices.ios import get_connected_devices as get_ios_devices
from app.utils.generic import get_timestamp


class DeviceOperationRunner(QObject):
    operation_started = Signal(str)
    operation_finished = Signal(str, str)  # serial, operation
    operation_error = Signal(str, str, str)  # serial, operation, message

    def __init__(self, max_workers: int = 4) -> None:
        super().__init__()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def submit(self, operation: Callable[..., object]) -> None:
        self._executor.submit(self._run, operation)

    def _run(self, operation: Callable[..., object]) -> None:
        try:
            result = operation()
            self.operation_finished.emit(result)
        except Exception:
            self.operation_error.emit()

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


class DeviceScanWorker(QObject):
    """Worker that runs device scans in a background thread."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._cancelled = False

    def cancel(self) -> None:
        """Set the cancellation flag."""
        self._cancelled = True

    @Slot()
    def run_scan(self) -> None:
        """Scan for Android and iOS devices."""
        logger.debug("DeviceScanWorker: Starting scan")
        try:
            devices: list[Device] = []

            if not self._cancelled:
                # Android devices
                try:
                    android_devices = get_android_devices()
                    logger.debug(
                        f"DeviceScanWorker: Android scan returned: {android_devices}"
                    )
                    if android_devices:
                        devices.extend(android_devices)
                except Exception as e:
                    logger.debug(f"Android scan failed: {e}")

            if not self._cancelled:
                # iOS devices
                try:
                    ios_devices = get_ios_devices()
                    logger.debug(f"DeviceScanWorker: iOS scan returned: {ios_devices}")
                    if ios_devices:
                        devices.extend(ios_devices)
                except Exception as e:
                    logger.debug(f"iOS scan failed: {e}")

            if self._cancelled:
                return

            logger.debug(f"DeviceScanWorker: Found {len(devices)} devices")
            self.finished.emit(devices)

        except Exception as e:
            logger.error(f"Device scan error: {e}")
            self.error.emit(str(e))


class ConnectedDevicesController(QObject):
    """Controller for managing device scanning and operations."""

    scan_started = Signal()
    scan_finished = Signal()
    scan_error = Signal(str)

    # Device list signal
    devices_updated = Signal(object)

    # Screenshot signals
    operation_started = Signal(str)
    operation_completed = Signal(str, str)
    operation_failed = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()

        self._output_directory: str = ""
        self._thread: QThread | None = None
        self._worker: DeviceScanWorker | None = None

        self._runner = DeviceOperationRunner()
        self._runner.operation_started.connect(self._on_operation_started)
        self._runner.operation_finished.connect(self._on_operation_finished)
        self._runner.operation_error.connect(self._on_operation_error)

    @Slot(str)
    def set_output_directory(self, directory: str) -> None:
        """Update the output directory for device operations."""
        self._output_directory = directory

    @Slot(Device)
    def take_screenshot(self, device: Device) -> None:
        """Take a screenshot of the specified device."""
        logger.debug(f"Taking screenshot of {device.os} device: {device.serial}")
        output_file = Path(self._output_directory) / f"screenshot_{get_timestamp()}.png"
        logger.info(f"Out: {output_file}")
        self._runner.submit(lambda: device.screenshot(output_file))
        self.operation_started.emit(device.identifier)

        # try:
        #     # Use polymorphic method - no string checking needed!
        #     result = device.screenshot(str(output_file))

        #     logger.info(f"Screenshot completed for {device.serial}: {result}")
        #     self.operation_completed.emit(device.identifier, result)

        # except Exception as e:
        #     logger.error(f"Screenshot failed for {device.serial}: {e}")
        #     self.operation_failed.emit(device.identifier, str(e))

    @Slot(Device)
    def backup(self, device: Device) -> None:
        """Take a backup of the specified device."""
        logger.debug(f"Taking backup of {device.os} device: {device.identifier}")
        output_file = Path(self._output_directory) / f"backup_{get_timestamp()}.ab"
        logger.info(f"Out: {output_file}")
        self._runner.submit(lambda: device.backup(str(output_file)))
        # self.operation_started.emit(device.identifier)

        # try:
        #     # Use polymorphic method - no string checking needed!
        #     result = device.backup(str(output_file))

        #     logger.info(f"Screenshot completed for {device.serial}: {result}")
        #     self.operation_completed.emit(device.identifier, result)

        # except Exception as e:
        #     logger.error(f"Screenshot failed for {device.serial}: {e}")
        #     self.operation_failed.emit(device.identifier, str(e))

    def start_scan(self) -> None:
        """Start a device scan in a background thread."""
        if self._thread and self._thread.isRunning():
            logger.warning("Device scan already in progress")
            return

        logger.info("Starting device scan")
        self.scan_started.emit()

        # Create thread and worker
        self._thread = QThread()
        self._worker = DeviceScanWorker()

        # Move worker to thread
        self._worker.moveToThread(self._thread)

        # Connect signals
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.error.connect(self._on_scan_error)
        self._thread.started.connect(self._worker.run_scan)
        self._thread.finished.connect(self._cleanup_thread)

        # Start the thread
        self._thread.start()

    def cancel_scan(self) -> None:
        """Cancel the current device scan."""
        if self._worker and self._thread and self._thread.isRunning():
            logger.info("Cancelling device scan")
            self._worker.cancel()

    @Slot(object)
    def _on_scan_finished(self, devices: list[Device]) -> None:
        """Handle successful device scan."""
        logger.info(f"Device scan completed: {len(devices)} devices")
        # Emit device list signal for other controllers
        self.devices_updated.emit(devices)
        self.scan_finished.emit()

        # Tell the thread to quit
        if self._thread:
            logger.debug("Telling thread to quit")
            self._thread.quit()

    @Slot(str)
    def _on_scan_error(self, error: str) -> None:
        """Handle device scan error."""
        logger.error(f"Device scan failed: {error}")
        self.scan_error.emit(error)

        # Tell the thread to quit even on error
        if self._thread:
            logger.debug("Telling thread to quit after error")
            self._thread.quit()

    @Slot()
    def _cleanup_thread(self) -> None:
        """Clean up thread and worker resources."""
        if self._thread:
            self._thread.deleteLater()
            self._thread = None
        if self._worker:
            self._worker.deleteLater()
            self._worker = None

    def _on_operation_started(self) -> None:
        pass

    def _on_operation_finished(self) -> None:
        pass

    def _on_operation_error(self) -> None:
        pass
