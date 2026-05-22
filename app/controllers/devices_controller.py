from typing import List

from loguru import logger
from PySide6.QtCore import QObject, Signal, Slot

from app.devices.devices import Device
from app.models.devices_model import DevicesModel
from app.views.devices_view import DevicesView


class DevicesController(QObject):
    # Signals for device operations
    screenshot_requested = Signal(Device)
    backup_requested = Signal(Device)
    connected_devices_updated = Signal(List[Device])

    def __init__(self, view: DevicesView, model: DevicesModel) -> None:
        super().__init__()

        self._view = view
        self._model = model

        self._view.screenshot_requested.connect(self._on_screenshot_requested)
        self._view.backup_requested.connect(self._on_backup_requested)

    @Slot(object)
    def _on_connected_devices_updated(self, connected_devices: List[Device]) -> None:
        """Handle device list updates and refresh the view."""
        logger.info(f"DevicesController received {len(connected_devices)} devices")
        # Update view with device list - assuming these are Device objects now
        self._view.update_devices(connected_devices)

    @Slot(str)
    def _on_operation_started(self, identifier: str) -> None:
        # Update the model
        pass
        # Model should update the view

    @Slot(Device)
    def _on_screenshot_requested(self, device: Device) -> None:
        """Handle screenshot request for a device and emit signal."""
        logger.info(f"Screenshot requested for {device.os} device: {device.identifier}")
        self.screenshot_requested.emit(device)

    @Slot(Device)
    def _on_backup_requested(self, device: Device) -> None:
        logger.info(f"Backup requested for {device.os} device: {device.identifier}")
        self.backup_requested.emit(device)
