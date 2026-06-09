from loguru import logger
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.devices.devices import ConnectionType, Device, OperationType
from app.views.dialogue_box import show_warning


class DeviceWidget(QWidget):
    """Widget for displaying a single device with screenshot button."""

    operation_requested = Signal(OperationType, Device)
    cancel_requested = Signal(Device)
    autoscroll_stop_requested = Signal(Device)

    def __init__(self, device: Device) -> None:
        super().__init__()

        self._device = device
        self._status = "Idle"
        self._autoscroll_active = False
        self._recording_active = False
        self._autoscroll_screenshot_active = False

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        self._heading_label = self._make_heading(layout)

        self._status_label = self._make_status_label(layout)

        self._warning_label = self._make_warning_label(layout)

        self._action_rows: list[tuple[QPushButton, QProgressBar]] = []
        self._enable_devmode_row = self._make_action_row(layout, "Enable Developer Mode", OperationType.ENABLE_DEV_MODE)
        if self._device.os == "iOS" and self._device.connection_type == ConnectionType.PARTIAL:
            self._enable_devmode_row[0].show()
        else:
            self._enable_devmode_row[0].hide()

        self._action_rows.extend(self._make_operation_grid(layout))

        self._action_rows.append(
            self._make_action_row(layout, "Start Screen Recording", OperationType.SCREEN_RECORDING)
        )

        self._combo_rows: list[tuple[QPushButton, QComboBox]] = []
        self._autoscroll_row = self._make_combo_row(
            layout, "Start Autoscroll", ["up", "down", "left", "right"], OperationType.AUTOSCROLL
        )
        self._autoscroll_btn, self._autoscroll_combo = self._autoscroll_row
        self._combo_rows.append(self._autoscroll_row)

        self._action_rows.append(self._make_action_row(layout, "Take Screenshot", OperationType.SCREENSHOT))

        self._autoscroll_screenshot_row = self._make_combo_row(
            layout,
            "Start Autoscroll Screenshot",
            ["up", "down", "left", "right"],
            OperationType.AUTOSCROLL_SCREENSHOT,
        )
        self._autoscroll_screenshot_btn, self._autoscroll_screenshot_combo = self._autoscroll_screenshot_row
        self._combo_rows.append(self._autoscroll_screenshot_row)

        self._cancel_btn = self._make_cancel_btn(layout)

        # Set initial state for buttons
        self._reset_btn_states()

        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #
    def _make_heading(self, layout: QVBoxLayout) -> QLabel:
        label = QLabel(self._device.device_name or self._device.identifier)
        font = label.font()
        font.setPointSize(18)
        font.setBold(True)
        label.setFont(font)
        label.setFixedHeight(label.fontMetrics().height())
        layout.addWidget(label)

        # label.setStyleSheet("background: red")
        return label

    def _make_status_label(self, layout: QVBoxLayout) -> QLabel:
        label = QLabel(self._generate_status_label())
        label.setFixedHeight(label.fontMetrics().height())
        layout.addWidget(label)

        # label.setStyleSheet("background: green")
        return label

    def _make_warning_label(self, layout: QVBoxLayout) -> QLabel:
        label = QLabel(self._get_warning_text())
        label.setFixedHeight(label.fontMetrics().height())
        label.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(label)

        if self._device.connection_type == ConnectionType.FULL:
            label.hide()

        # label.setStyleSheet("background: blue")
        return label

    def _make_action_row(
        self, layout: QVBoxLayout, label: str, operation: OperationType
    ) -> tuple[QPushButton, QProgressBar]:
        btn = QPushButton(label)
        bar = QProgressBar(minimum=0, maximum=0)
        bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(lambda: self._on_action_row_clicked(label, btn, bar, operation))
        bar.hide()
        layout.addWidget(btn)
        layout.addWidget(bar)

        # btn.setStyleSheet("background: red;")

        return (btn, bar)

    def _make_operation_grid(self, layout: QVBoxLayout) -> list[tuple[QPushButton, QProgressBar]]:
        grid = QGridLayout()
        action_rows: list[tuple[QPushButton, QProgressBar]] = []
        cell, btn, bar = self._make_operation_cell("Backup", OperationType.BACKUP)
        grid.addLayout(cell, 0, 0)
        action_rows.append((btn, bar))

        cell, btn, bar = self._make_operation_cell("Extract Contacts", OperationType.EXTRACT_CONTACTS)
        grid.addLayout(cell, 0, 1)
        action_rows.append((btn, bar))

        cell, btn, bar = self._make_operation_cell("Extract Device Info", OperationType.EXTRACT_DEVICE_INFO)
        grid.addLayout(cell, 1, 0)
        action_rows.append((btn, bar))

        cell, btn, bar = self._make_operation_cell("Extract Device Logs", OperationType.EXTRACT_DEVICE_LOGS)
        grid.addLayout(cell, 1, 1)
        action_rows.append((btn, bar))

        layout.addLayout(grid)
        return action_rows

    def _make_operation_cell(
        self, label: str, operation: OperationType
    ) -> tuple[QVBoxLayout, QPushButton, QProgressBar]:
        cell = QVBoxLayout()
        btn, bar = self._make_action_row(cell, label, operation)
        return cell, btn, bar

    def _make_combo_row(
        self, layout: QVBoxLayout, btn_label: str, combo_labels: list[str], operation: OperationType
    ) -> tuple[QPushButton, QComboBox]:
        widget = QWidget()
        # widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sublayout = QHBoxLayout()
        sublayout.setContentsMargins(0, 0, 0, 0)
        sublayout.setSpacing(1)
        btn = QPushButton(btn_label)
        combo = QComboBox()
        combo.addItems(combo_labels)
        btn.clicked.connect(lambda: self._on_combo_row_clicked(combo.currentText(), operation))

        sublayout.addWidget(btn)
        sublayout.addWidget(combo)
        widget.setLayout(sublayout)
        layout.addWidget(widget)

        return btn, combo

    def _make_cancel_btn(self, layout: QVBoxLayout) -> QPushButton:
        btn = QPushButton("Cancel")
        btn.clicked.connect(self._on_cancel_requested)

        btn.setStyleSheet("QPushButton { background-color: red; }")
        policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        policy.setRetainSizeWhenHidden(True)
        btn.setSizePolicy(policy)
        btn.hide()

        layout.addWidget(btn)

        return btn

    def _reset_btn_states(self) -> None:
        for btn, bar in self._action_rows:
            btn.show()
            bar.hide()

            if self._device.connection_type == ConnectionType.NONE or (
                self._device.connection_type == ConnectionType.PARTIAL and "Screenshot" in btn.text()
            ):
                btn.setDisabled(True)
                continue
            btn.setEnabled(True)

        for btn, combo in self._combo_rows:
            if self._device.connection_type == ConnectionType.NONE or (
                self._device.connection_type == ConnectionType.PARTIAL and "Screenshot" in btn.text()
            ):
                btn.setDisabled(True)
                combo.setDisabled(True)
                continue
            btn.setEnabled(True)
            combo.setEnabled(True)

    # ------------------------------------------------------------------ #
    # Public
    # ------------------------------------------------------------------ #
    def set_busy(self, operation: OperationType) -> None:
        if operation == OperationType.IDLE:
            self._autoscroll_active = False
            self._recording_active = False
            self._autoscroll_btn.setText("Start Autoscroll")
            self._status = "Idle"
            self._status_label.setText(self._generate_status_label())
            self._apply_busy_state()
            return

        if operation == OperationType.SCREEN_RECORDING:
            self._recording_active = True

        if self._autoscroll_active or self._recording_active:
            # Concurrent autoscroll/recording: derive state from flags
            self._apply_busy_state()
            return

        # Generic operation (screenshot, backup, etc.) with no concurrent special operations.
        # Disable all buttons without touching bar/button visibility set by _on_action_row_clicked.
        for btn, bar in self._action_rows:
            btn.setDisabled(True)
        for btn, combo in self._combo_rows:
            btn.setDisabled(True)
            combo.setDisabled(True)
        if operation != OperationType.ENABLE_DEV_MODE:
            self._cancel_btn.show()
            self._cancel_btn.setEnabled(True)

    def _apply_busy_state(self) -> None:
        """Derive all button states from _autoscroll_active and _recording_active."""
        if not self._autoscroll_active and not self._recording_active:
            self._reset_btn_states()
            self._cancel_btn.hide()
            self._cancel_btn.setDisabled(True)
            return

        for btn, bar in self._action_rows:
            if not self._recording_active:
                # Autoscroll only: keep screen recording and screenshot available
                is_screenshot = "Screenshot" in btn.text()
                is_recording_btn = btn.text() == "Start Screen Recording"
                if is_screenshot or is_recording_btn:
                    if self._device.connection_type == ConnectionType.NONE or (
                        self._device.connection_type == ConnectionType.PARTIAL and is_screenshot
                    ):
                        btn.setDisabled(True)
                    else:
                        btn.setEnabled(True)
                    continue
            btn.setDisabled(True)

        for btn, combo in self._combo_rows:
            if btn is self._autoscroll_btn:
                btn.setEnabled(True)
                combo.setEnabled(not self._autoscroll_active)
            else:
                btn.setDisabled(True)
                combo.setDisabled(True)

        if self._recording_active:
            self._cancel_btn.show()
            self._cancel_btn.setEnabled(True)
        else:
            self._cancel_btn.hide()
            self._cancel_btn.setDisabled(True)

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

        if self._device.os == "iOS" and self._device.connection_type == ConnectionType.PARTIAL:
            self._enable_devmode_row[0].show()
        else:
            self._enable_devmode_row[0].hide()
            self._enable_devmode_row[1].hide()

        if full_connection:
            self._warning_label.hide()
        else:
            self._warning_label.setText(self._get_warning_text())
            self._warning_label.show()

        for btn, _ in self._action_rows:
            btn.setEnabled(full_connection or (partial_connection and "Screenshot" not in btn.text()))

        for btn, combo in self._combo_rows:
            btn.setEnabled(full_connection or (partial_connection and "Screenshot" not in btn.text()))
            combo.setEnabled(full_connection or (partial_connection and "Screenshot" not in btn.text()))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _generate_status_label(self) -> str:
        parts = []
        if self._device.serial:
            parts.append(f"Serial: {self._device.serial}")

        if self._device.os == "iOS":
            parts.append(f"UDID: {self._device.identifier}")

        parts.append(
            f"OS: {self._device.os} ({self._device.os_version})"
            if self._device.os_version
            else f"OS: {self._device.os}"
        )

        if self._device.device_type:
            parts.append(f"Device Type: {self._device.device_type}")

        # if d.width and d.height:
        #     parts.append(f"Dimensions: {d.width}x{d.height}")

        parts.append(f"Status: {self._status}")
        return " | ".join(parts)

    def _on_action_row_clicked(self, label: str, btn: QPushButton, bar: QProgressBar, operation: OperationType) -> None:
        logger.info(f"Pressed {label} with action {operation.name}")
        self._status = label
        self._status_label.setText(self._generate_status_label())
        btn.hide()
        bar.setValue(0)
        bar.show()
        self.operation_requested.emit(operation, self._device)

    def _on_combo_row_clicked(
        self,
        selection: str,
        operation: OperationType,
    ) -> None:
        logger.info(f"Pressed {selection}")
        if operation == OperationType.AUTOSCROLL:
            if self._autoscroll_active:
                # Stop autoscroll
                self._on_autoscroll_stop_requested()
            else:
                # Start autoscroll - set active state immediately for UI feedback
                self._autoscroll_active = True
                self._autoscroll_btn.setText("Stop Autoscroll")
                self._autoscroll_combo.setEnabled(False)
                match selection:
                    case "up":
                        self.operation_requested.emit(OperationType.AUTOSCROLL_UP, self._device)
                    case "down":
                        self.operation_requested.emit(OperationType.AUTOSCROLL_DOWN, self._device)
                    case "left":
                        self.operation_requested.emit(OperationType.AUTOSCROLL_LEFT, self._device)
                    case "right":
                        self.operation_requested.emit(OperationType.AUTOSCROLL_RIGHT, self._device)
        elif operation == OperationType.AUTOSCROLL_SCREENSHOT:
            match selection:
                case "up":
                    self.operation_requested.emit(OperationType.AUTOSCROLL_SCREENSHOT_UP, self._device)
                case "down":
                    self.operation_requested.emit(OperationType.AUTOSCROLL_SCREENSHOT_DOWN, self._device)
                case "left":
                    self.operation_requested.emit(OperationType.AUTOSCROLL_SCREENSHOT_LEFT, self._device)
                case "right":
                    self.operation_requested.emit(OperationType.AUTOSCROLL_SCREENSHOT_RIGHT, self._device)

    def _on_autoscroll_stop_requested(self) -> None:
        """Handle stopping autoscroll."""
        self._autoscroll_active = False
        self._autoscroll_btn.setText("Start Autoscroll")
        self.autoscroll_stop_requested.emit(self._device)
        self._apply_busy_state()

    def set_autoscroll_finished(self) -> None:
        """Called when autoscroll operation has finished (not via stop button)."""
        self._autoscroll_active = False
        self._autoscroll_btn.setText("Start Autoscroll")
        self._apply_busy_state()

    def set_recording_finished(self) -> None:
        """Called when recording has finished while autoscroll may still be running."""
        self._recording_active = False
        self._apply_busy_state()

    def _get_warning_text(self) -> str:
        if self._device.os == "Android":
            if self._device.connection_type == ConnectionType.NONE:
                return (
                    "Warning: Connection unauthorised. Please unlock phone and enable/allow USB debugging to continue."
                )
        elif self._device.os == "iOS":
            if self._device.connection_type == ConnectionType.NONE:
                return "Warning: Cannot establish connection. An MDM may be active on the device."
            elif self._device.connection_type == ConnectionType.PARTIAL:
                return "Warning: Device not in developer mode. Screenshot functionality is unavailable."

        return ""

    def _on_cancel_requested(self) -> None:
        self._cancel_btn.setDisabled(True)
        self.cancel_requested.emit(self._device)
