from typing import List

from loguru import logger
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.devices.devices import Device


class DeviceWidget(QWidget):
    """Widget for displaying a single device with screenshot button."""

    screenshot_requested = Signal(Device)
    backup_requested = Signal(Device)

    def __init__(self, device: Device) -> None:
        super().__init__()
        self._device = device

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


class DevicesView(QWidget):
    screenshot_requested = Signal(Device)
    backup_requested = Signal(Device)

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

    def update_devices(self, devices: List[Device]) -> None:
        """Update the device list display."""
        # Clear existing widgets
        for widget in self._device_widgets:
            widget.deleteLater()
        self._device_widgets.clear()

        # Add new device widgets
        for device in devices:
            device_widget = DeviceWidget(device)
            device_widget.screenshot_requested.connect(self.screenshot_requested.emit)
            device_widget.backup_requested.connect(self.backup_requested.emit)
            self._devices_layout.addWidget(device_widget)
            self._device_widgets.append(device_widget)

        logger.debug(f"Updated DevicesView with {len(devices)} devices")
