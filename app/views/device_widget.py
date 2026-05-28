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

from app.devices.devices import Device


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

        self._warning_label = QLabel(
            "Warning: Connection unauthorised. Please unlock phone and allow USB debugging to continue."
        )
        self._warning_label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(self._warning_label)

        if self._device.connection_allowed:
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

        if not self._device.connection_allowed:
            for btn, _ in self._action_rows:
                btn.setDisabled(True)

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
            btn.setEnabled(not busy)
            if not busy:
                btn.show()
                bar.hide()

        if not busy:
            self._status = "Idle"
            self._status_label.setText(self._generate_status_label())
            self.set_progress(0, 0)

    @Slot(str)
    def set_status(self, status: str) -> None:
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
        if self._device.connection_allowed:
            self._warning_label.hide()
            for btn, _ in self._action_rows:
                btn.setEnabled(True)
        else:
            self._warning_label.show()
            for btn, _ in self._action_rows:
                btn.setDisabled(True)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _generate_status_label(self) -> str:
        d = self._device
        os_str = f"{d.os} ({d.os_version})" if d.os_version else d.os
        parts = [f"Serial: {d.serial}", f"OS: {os_str}"]
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
        self._cancel_btn.show()
        signal.emit(self._device)
