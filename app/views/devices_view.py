from typing import List

from loguru import logger
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.devices.devices import Device
from app.views.dialogue import show_warning


class DeviceWidget(QWidget):
    """Widget for displaying a single device with screenshot button."""

    screenshot_requested = Signal(Device)
    backup_requested = Signal(Device)

    def __init__(self, device: Device) -> None:
        super().__init__()
        self._device = device
        self._device_id = device.identifier

        layout = QHBoxLayout()

        # Device info label
        device_text = device.get_info()
        self._label = QLabel(device_text)
        layout.addWidget(self._label)

        # Screenshot button
        self._screenshot_btn = QPushButton("Screenshot")
        self._screenshot_btn.clicked.connect(self._on_screenshot_clicked)
        layout.addWidget(self._screenshot_btn)

        self._backup_btn = QPushButton("Backup")
        self._backup_btn.clicked.connect(self._on_backup_clicked)
        layout.addWidget(self._backup_btn)

        layout.addStretch()
        self.setLayout(layout)

    def _on_screenshot_clicked(self) -> None:
        """Handle screenshot button click."""
        logger.info(
            f"Screenshot requested for {self._device.os} device: {self._device.identifier}"
        )
        self.screenshot_requested.emit(self._device)

    def _on_backup_clicked(self) -> None:
        logger.info(
            f"Backup requested for {self._device.os} device: {self._device.identifier}"
        )
        self.backup_requested.emit(self._device)

    def set_busy(self, busy: bool) -> None:
        """Enable or disable buttons based on operation state."""
        self._screenshot_btn.setEnabled(not busy)
        self._backup_btn.setEnabled(not busy)


class DevicesView(QWidget):
    screenshot_requested = Signal(Device)
    backup_requested = Signal(Device)
    operation_error = Signal(str, str)  # title, message

    def __init__(self) -> None:
        super().__init__()
        logger.debug("Initializing DevicesView")

        self._layout = QVBoxLayout()
        self._device_widgets: List[DeviceWidget] = []

        # Title
        title = QLabel("Connected Devices")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self._layout.addWidget(title)

        # Scroll area for device list
        self._devices_container = QWidget()
        self._devices_layout = QVBoxLayout()
        self._devices_container.setLayout(self._devices_layout)
        self._layout.addWidget(self._devices_container)

        self._layout.addStretch()
        self.setLayout(self._layout)
        self._device_widget_map: dict[str, DeviceWidget] = {}

        # Wire error signal to show_warning
        self.operation_error.connect(self._on_operation_error)

    def update_devices(self, devices: List[Device]) -> None:
        """Update the device list display."""
        # Clear existing widgets
        for widget in self._device_widgets:
            widget.deleteLater()
        self._device_widgets.clear()
        self._device_widget_map.clear()

        # Add new device widgets
        for device in devices:
            device_widget = DeviceWidget(device)
            device_widget.screenshot_requested.connect(self.screenshot_requested.emit)
            device_widget.backup_requested.connect(self.backup_requested.emit)
            self._devices_layout.addWidget(device_widget)
            self._device_widgets.append(device_widget)
            self._device_widget_map[device.identifier] = device_widget

        logger.debug(f"Updated DevicesView with {len(devices)} devices")

    def set_device_busy(self, device_id: str, busy: bool) -> None:
        """Set busy state for a specific device widget."""
        if device_id in self._device_widget_map:
            self._device_widget_map[device_id].set_busy(busy)

    def show_operation_failed_warning(self, title: str, message: str) -> None:
        show_warning(title, message)

    @Slot(str, str)
    def _on_operation_error(self, title: str, message: str) -> None:
        """Handle operation error signal."""
        show_warning(title, message)
