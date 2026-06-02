from loguru import logger
from PySide6.QtCore import Signal, SignalInstance, Slot
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.devices.devices import ConnectionType, Device
from app.views.dialogue_box import show_warning


class DeviceWidget(QWidget):
    """Widget for displaying a single device with screenshot button."""

    backup_requested = Signal(Device)
    extract_contacts_requested = Signal(Device)
    extract_device_info_requested = Signal(Device)
    extract_device_logs_requested = Signal(Device)
    screen_recording_requested = Signal(Device)
    screenshot_requested = Signal(Device)
    cancel_requested = Signal(Device)

    def __init__(self, device: Device) -> None:
        super().__init__()
        self._device = device
        self._status = "Idle"

        layout = QVBoxLayout()
        self._heading_label = self._make_heading(
            device.device_name or device.identifier
        )
        layout.addWidget(self._heading_label)

        self._status_label = QLabel(self._generate_status_label())
        layout.addWidget(self._status_label)

        self._warning_label = QLabel(self._get_warning_text())
        self._warning_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self._warning_label)

        if self._device.connection_type == ConnectionType.FULL:
            self._warning_label.hide()

        self._action_rows: list[tuple[QPushButton, QProgressBar]] = []

        # --- 2x2 grid for backup/extraction buttons ---
        grid = QGridLayout()
        grid_actions = [
            ("Backup", self.backup_requested),
            ("Extract Contacts", self.extract_contacts_requested),
            ("Extract Device Info", self.extract_device_info_requested),
            ("Extract Device Logs", self.extract_device_logs_requested),
        ]
        for idx, (label, signal) in enumerate(grid_actions):
            btn, bar = self._create_action_pair(label, signal)
            self._action_rows.append((btn, bar))
            cell = QVBoxLayout()
            cell.addWidget(btn)
            cell.addWidget(bar)
            grid.addLayout(cell, idx // 2, idx % 2)
        layout.addLayout(grid)

        # --- Full-width buttons below ---
        self._action_rows.append(
            self._add_action_row(
                layout, "Screen Recording", self.screen_recording_requested
            )
        )
        self._action_rows.append(
            self._add_action_row(layout, "Screenshot", self.screenshot_requested)
        )

        for btn, _ in self._action_rows:
            full_connection = self._device.connection_type == ConnectionType.FULL
            partial_connection = self._device.connection_type == ConnectionType.PARTIAL
            btn.setEnabled(
                full_connection or (partial_connection and btn.text() != "Screenshot")
            )

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.hide()
        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        policy.setRetainSizeWhenHidden(True)
        self._cancel_btn.setSizePolicy(policy)
        self._cancel_btn.setStyleSheet(
            "QPushButton { background-color: red; color: white; }"
        )
        self._cancel_btn.clicked.connect(
            lambda: self.cancel_requested.emit(self._device)
        )
        layout.addWidget(self._cancel_btn)

        layout.addStretch()
        self.setLayout(layout)

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #
    def _make_heading(self, text: str) -> QLabel:
        label = QLabel(text)
        font = label.font()
        font.setPointSize(18)
        font.setBold(True)
        label.setFont(font)
        return label

    def _create_action_pair(
        self, label: str, signal: SignalInstance
    ) -> tuple[QPushButton, QProgressBar]:
        btn = QPushButton(label)
        bar = QProgressBar(minimum=0, maximum=0)
        bar.hide()
        btn.clicked.connect(lambda: self._on_action_clicked(label, signal, btn, bar))
        return btn, bar

    def _add_action_row(
        self, layout: QVBoxLayout, label: str, signal: SignalInstance
    ) -> tuple[QPushButton, QProgressBar]:
        btn, bar = self._create_action_pair(label, signal)
        layout.addWidget(btn)
        layout.addWidget(bar)
        return btn, bar

    # ------------------------------------------------------------------ #
    # Public
    # ------------------------------------------------------------------ #
    def set_busy(self, busy: bool) -> None:
        self._cancel_btn.setHidden(not busy)
        for btn, bar in self._action_rows:
            full_connection = self._device.connection_type == ConnectionType.FULL
            partial_connection = self._device.connection_type == ConnectionType.PARTIAL
            btn.setEnabled(
                not busy
                and (
                    full_connection
                    or (partial_connection and btn.text() != "Screenshot")
                )
            )
            # btn.setEnabled(not busy)
            if not busy:
                btn.show()
                bar.hide()

        if not busy:
            self._status = "Idle"
            self._status_label.setText(self._generate_status_label())
            self.set_progress(0, 0)

    @Slot(str)
    def set_status(self, status: str) -> None:
        if status == "UXPLAY_ENTER_PIN":
            show_warning("Enter Pin", "Enter pin '1234' on the device to continue")
            return
        self._status = status
        self._status_label.setText(self._generate_status_label())

    @Slot(int, int)
    def set_progress(self, current: int, total: int) -> None:
        for _, bar in self._action_rows:
            if total <= 0:
                bar.setRange(0, 0)
            else:
                bar.setRange(0, total)
                bar.setValue(current)

    def update_widget(self, device: Device) -> None:
        self._device = device
        logger.info(f"Name: {device.device_name}, ID: {device.identifier}")
        self._heading_label.setText(self._device.device_name or self._device.identifier)
        self._status_label.setText(self._generate_status_label())

        full_connection = self._device.connection_type == ConnectionType.FULL
        partial_connection = self._device.connection_type == ConnectionType.PARTIAL

        if full_connection:
            self._warning_label.hide()
        else:
            self._warning_label.setText(self._get_warning_text())
            self._warning_label.show()

        for btn, _ in self._action_rows:
            btn.setEnabled(
                full_connection or (partial_connection and btn.text() != "Screenshot")
            )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _generate_status_label(self) -> str:
        d = self._device
        parts = []
        if d.serial:
            parts.append(f"Serial: {d.serial}")

        if d.os == "iOS":
            parts.append(f"UDID: {d.identifier}")

        parts.append(f"OS: {d.os} ({d.os_version})" if d.os_version else f"OS: {d.os}")

        if d.device_type:
            parts.append(f"Device Type: {d.device_type}")
        parts.append(f"Status: {self._status}")
        return " | ".join(parts)

    def _on_action_clicked(
        self, status: str, signal: SignalInstance, btn: QPushButton, bar: QProgressBar
    ) -> None:
        logger.info(
            f"{status} requested for {self._device.os} device: {self._device.identifier}"
        )
        self._status = status
        self._status_label.setText(self._generate_status_label())
        btn.hide()
        bar.show()
        self._cancel_btn.setText(
            "Stop Recording"
        ) if self._status == "Screen Recording" else self._cancel_btn.setText("Cancel")
        self._cancel_btn.show()

        signal.emit(self._device)

    def _get_warning_text(self) -> str:
        if self._device.os == "Android":
            if self._device.connection_type == ConnectionType.NONE:
                return "Warning: Connection unauthorised. Please unlock phone and enable/allow USB debugging to continue."
        elif self._device.os == "iOS":
            if self._device.connection_type == ConnectionType.NONE:
                return "Warning: Cannot establish connection. An MDM may be active on the device."
            elif self._device.connection_type == ConnectionType.PARTIAL:
                return "Warning: Device not in developer mode. Screenshot functionality is unavailable."

        return ""
