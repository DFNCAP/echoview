from collections.abc import Callable

from loguru import logger
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.devices.devices import Device, OperationType
from app.views.device_widget import DeviceWidget
from app.views.dialogue_box import show_warning
from app.views.message_box import BinaryChoiceDialog


class DevicesView(QWidget):
    operation_requested = Signal(OperationType, Device)
    combo_operation_requested = Signal(OperationType, Device, str)
    cancel_requested = Signal(Device)
    autoscroll_stop_requested = Signal(Device)

    def __init__(self) -> None:
        super().__init__()
        logger.debug("Initializing DevicesView")
        self._device_widget_map: dict[str, DeviceWidget] = {}

        self._layout = QVBoxLayout()

        # Title with spinner
        title_layout = QHBoxLayout()
        title = QLabel("Connected Devices")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_layout.addWidget(title)

        # Scanning indicator
        self._scanning_label = QLabel(" - Scanning")
        # self._scanning_label.setStyleSheet("color: #666;")
        self._spinner = QLabel("⟳")
        self._spinner.setStyleSheet("font-size: 14px;")
        self._spinner.hide()
        self._scanning_label.hide()

        # Spinner animation using character rotation
        self._spinner_chars = ["|", "/", "-", "\\"]
        self._spinner_index = 0
        self._spinner_timer = QTimer()
        self._spinner_timer.timeout.connect(self._update_spinner)
        self._spinner_timer.setInterval(100)

        title_layout.addWidget(self._scanning_label)
        title_layout.addWidget(self._spinner)
        title_layout.addStretch()
        self._layout.addLayout(title_layout)

        self._scroll_area = QScrollArea()
        self._scroll_area.setContentsMargins(0, 0, 0, 0)

        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Scroll area for device list
        self._devices_container = QWidget()
        self._devices_container.setContentsMargins(0, 0, 0, 0)

        self._devices_layout = QVBoxLayout()
        self._devices_layout.setSpacing(10)
        self._devices_layout.setContentsMargins(0, 0, 0, 0)
        self._devices_container.setLayout(self._devices_layout)
        self._devices_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._scroll_area.setWidget(self._devices_container)
        self._layout.addWidget(self._scroll_area)

        # self._layout.addStretch()
        self.setLayout(self._layout)

    def _update_spinner(self) -> None:
        """Update the spinner character."""
        self._spinner.setText(self._spinner_chars[self._spinner_index])
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)

    def set_scanning(self, scanning: bool) -> None:
        """Show or hide the scanning indicator."""
        if scanning:
            self._scanning_label.show()
            self._spinner.show()
            self._spinner_timer.start()
        else:
            self._scanning_label.hide()
            self._spinner.hide()
            self._spinner_timer.stop()

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
                device_widget.operation_requested.connect(self.operation_requested.emit)
                device_widget.combo_operation_requested.connect(self.combo_operation_requested.emit)
                device_widget.autoscroll_stop_requested.connect(self.autoscroll_stop_requested.emit)
                device_widget.cancel_requested.connect(self.cancel_requested)
                self._devices_layout.addWidget(device_widget)
                self._device_widget_map[device.identifier] = device_widget
            else:
                # Existing device - update the device reference
                self._device_widget_map[device.identifier].update_widget(device)

        logger.debug(f"Updated DevicesView with {len(devices)} devices")

    def set_device_busy(self, device_id: str, operation: OperationType) -> None:
        """Set busy state for a specific device widget."""
        if device_id in self._device_widget_map:
            self._device_widget_map[device_id].set_busy(operation)

    def get_widget(self, identifier: str) -> QWidget | None:
        return self._device_widget_map.get(identifier)

    @Slot(str, str)
    def set_status(self, identifier: str, status: str) -> None:
        widget = self._device_widget_map.get(identifier)
        if widget:
            widget.set_status(status)

    @Slot(str, int, int)
    def set_progress(self, identifier: str, current: int, total: int) -> None:
        widget = self._device_widget_map.get(identifier)
        if widget:
            widget.set_progress(current, total)

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
