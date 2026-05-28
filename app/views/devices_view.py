from collections.abc import Callable

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
from app.views.device_widget import DeviceWidget
from app.views.dialogue_box import show_warning
from app.views.message_box import BinaryChoiceDialog


class DevicesView(QWidget):
    backup_requested = Signal(Device)
    extract_contacts_requested = Signal(Device)
    extract_device_info_requested = Signal(Device)
    extract_device_logs_requested = Signal(Device)
    screen_recording_requested = Signal(Device)
    screenshot_requested = Signal(Device)
    cancel_requested = Signal(Device)

    def __init__(self) -> None:
        super().__init__()
        logger.debug("Initializing DevicesView")
        self._device_widget_map: dict[str, DeviceWidget] = {}

        self._layout = QVBoxLayout()

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

    @Slot(object)
    def update_devices(self, devices: list[Device]) -> None:
        """Update the device list display, preserving existing widgets."""
        # Get current device IDs
        current_ids = {d.identifier for d in devices}
        existing_ids = set(self._device_widget_map.keys())

        # Remove devices that are no longer connected
        for device_id in existing_ids - current_ids:
            widget = self._device_widget_map[device_id]
            widget.deleteLater()
            del self._device_widget_map[device_id]

        # Add or update devices
        for device in devices:
            if device.identifier not in self._device_widget_map:
                # New device - create widget
                device_widget = DeviceWidget(device)
                device_widget.backup_requested.connect(self.backup_requested.emit)
                device_widget.screen_recording_requested.connect(
                    self.screen_recording_requested.emit
                )
                device_widget.screenshot_requested.connect(
                    self.screenshot_requested.emit
                )
                device_widget.cancel_requested.connect(self.cancel_requested)
                self._devices_layout.addWidget(device_widget)
                self._device_widget_map[device.identifier] = device_widget
            else:
                # Existing device - update the device reference
                self._device_widget_map[device.identifier].update_widget(device)

        logger.debug(f"Updated DevicesView with {len(devices)} devices")

    def set_device_busy(self, device_id: str, busy: bool) -> None:
        """Set busy state for a specific device widget."""
        if device_id in self._device_widget_map:
            self._device_widget_map[device_id].set_busy(busy)

    def show_operation_waring(self, title: str, message: str) -> None:
        show_warning(title, message)

    def show_binary_choice(self, title: str, text: str, information: str) -> bool:
        binary_diag = BinaryChoiceDialog(
            title=title,
            text=text,
            information=information,
            positive_text="Yes",
            negative_text="No",
        )

        return binary_diag.exec_is_positive()
