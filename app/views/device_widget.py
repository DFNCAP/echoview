from loguru import logger
from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
    combo_operation_requested = Signal(OperationType, Device, str)
    cancel_requested = Signal(Device)
    autoscroll_stop_requested = Signal(Device)

    def __init__(self, device: Device) -> None:
        super().__init__()

        self._device = device
        self._status = ""
        self._autoscroll_active = False
        self._recording_active = False
        self._autoscroll_screenshot_active = False

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        # layout.setSpacing(1)

        self._heading_label = self._make_title_label(layout)

        self._details_label = self._make_details_label(layout)
        self._status_label = self._make_status_label(layout)

        self._warning_label = self._make_warning_label(layout)

        self._action_rows: list[tuple[QPushButton, QProgressBar]] = []
        enable_devmode_row = self._make_action_row(layout, "Enable Developer Mode", OperationType.ENABLE_DEV_MODE)
        self._enable_devmode_btn, self._enable_devmode_bar = enable_devmode_row
        if self._device.os == "iOS" and self._device.connection_type == ConnectionType.PARTIAL:
            self._enable_devmode_btn.show()
        else:
            self._enable_devmode_btn.hide()

        self._exhibit_number_input = self._make_exhibit_number_input(layout)

        self._action_rows.extend(self._make_operation_grid(layout))

        self._action_rows.append(
            self._make_action_row(layout, "Start Screen Recording", OperationType.SCREEN_RECORDING)
        )
        self._action_rows.append(self._make_action_row(layout, "Take Screenshot", OperationType.SCREENSHOT))

        self._combo_rows: list[tuple[QPushButton, QComboBox]] = []

        autoscroll_row = self._make_combo_row(
            layout, "Start Autoscroll", ["up", "down", "left", "right"], OperationType.AUTOSCROLL
        )
        self._autoscroll_btn, self._autoscroll_combo = autoscroll_row
        self._combo_rows.append(autoscroll_row)

        autoscroll_screenshot_row = self._make_combo_row(
            layout,
            "Start Autoscroll Screenshot",
            ["up", "down", "left", "right"],
            OperationType.AUTOSCROLL_SCREENSHOT,
        )
        self._autoscroll_screenshot_btn, self._autoscroll_screenshot_combo = autoscroll_screenshot_row
        self._combo_rows.append(autoscroll_screenshot_row)

        self._cancel_btn = self._make_cancel_btn(layout)

        # Set initial state for buttons
        self._reset_btn_states()

        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    # ------------------------------------------------------------------ #
    # Setup
    # ------------------------------------------------------------------ #
    def _make_title_label(self, layout: QBoxLayout) -> QLabel:
        label = QLabel(self._device.device_name or self._device.identifier)
        font = label.font()
        font.setPointSize(18)
        font.setBold(True)
        label.setFont(font)
        label.setFixedHeight(label.fontMetrics().height())
        layout.addWidget(label)

        # label.setStyleSheet("background: red")
        return label

    def _make_status_label(self, layout: QBoxLayout) -> QLabel:
        label = QLabel(self._status)
        # label.setAlignment(Qt.AlignmentFlag.AlignRight)
        font = label.font()
        font.setPointSize(12)
        # font.setBold(True)
        label.setFont(font)
        label.setFixedHeight(label.fontMetrics().height())
        layout.addWidget(label)

        return label

    def _make_details_label(self, layout: QVBoxLayout) -> QLabel:
        label = QLabel(self._generate_details_label())
        label.setFixedHeight(label.fontMetrics().height())
        layout.addWidget(label)
        return label

    def _make_warning_label(self, layout: QVBoxLayout) -> QLabel:
        label = QLabel(self._get_warning_text())
        label.setFixedHeight(label.fontMetrics().height())
        label.setForegroundRole(QPalette.ColorRole.BrightText)
        label.setStyleSheet("font-weight: bold;")
        layout.addWidget(label)

        if self._device.connection_type == ConnectionType.FULL:
            label.hide()
        return label

    def _make_exhibit_number_input(self, layout: QVBoxLayout) -> QLineEdit:
        exhibit_number = QLineEdit(placeholderText="Exhibit Number")
        exhibit_number.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        exhibit_number.editingFinished.connect(self._on_exhibit_number_changed)
        layout.addWidget(exhibit_number)

        return exhibit_number

    def _on_exhibit_number_changed(self) -> None:
        self._device.exhibit_id = self._exhibit_number_input.text()

    def _make_action_row(
        self, layout: QVBoxLayout, label: str, operation: OperationType
    ) -> tuple[QPushButton, QProgressBar]:
        btn = QPushButton(label)
        bar = QProgressBar(minimum=0, maximum=0)
        bar.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(lambda: self._on_action_row_clicked(btn, bar, operation))
        bar.hide()
        layout.addWidget(btn)
        layout.addWidget(bar)
        return (btn, bar)

    def _make_operation_grid(self, layout: QVBoxLayout) -> list[tuple[QPushButton, QProgressBar]]:
        grid = QGridLayout()
        action_rows: list[tuple[QPushButton, QProgressBar]] = []

        cell = QVBoxLayout()
        btn, bar = self._make_action_row(cell, "Backup", OperationType.BACKUP)
        grid.addLayout(cell, 0, 0)
        action_rows.append((btn, bar))

        cell = QVBoxLayout()
        btn, bar = self._make_action_row(cell, "Extract Contacts", OperationType.EXTRACT_CONTACTS)
        grid.addLayout(cell, 0, 1)
        action_rows.append((btn, bar))

        cell = QVBoxLayout()
        btn, bar = self._make_action_row(cell, "Extract Device Info", OperationType.EXTRACT_DEVICE_INFO)
        grid.addLayout(cell, 1, 0)
        action_rows.append((btn, bar))

        cell = QVBoxLayout()
        btn, bar = self._make_action_row(cell, "Extract Device Logs", OperationType.EXTRACT_DEVICE_LOGS)
        grid.addLayout(cell, 1, 1)
        action_rows.append((btn, bar))

        layout.addLayout(grid)
        return action_rows

    def _make_combo_row(
        self, layout: QVBoxLayout, btn_label: str, combo_labels: list[str], operation: OperationType
    ) -> tuple[QPushButton, QComboBox]:
        sublayout = QHBoxLayout()
        btn = QPushButton(btn_label)
        combo = QComboBox()
        combo.addItems(combo_labels)
        btn.clicked.connect(lambda: self._on_combo_row_clicked(btn, combo, operation))

        sublayout.addWidget(btn)
        sublayout.addWidget(combo)
        layout.addLayout(sublayout)

        return btn, combo

    def _make_cancel_btn(self, layout: QVBoxLayout) -> QPushButton:
        btn = QPushButton("Cancel")
        btn.clicked.connect(self._on_cancel_requested)

        # btn.setStyleSheet("QPushButton { background-color: red; }")
        btn.setStyleSheet("QPushButton {background-color: palette(bright-text); color: palette(window); }")
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
            bar.setRange(0, 0)

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

        self._cancel_btn.setText("Cancel")

    # ------------------------------------------------------------------ #
    # Public
    # ------------------------------------------------------------------ #
    def set_busy(self, operation: OperationType) -> None:
        logger.debug(f"Setting busy for operation {operation.name} for device {self._device.identifier}")
        match operation:
            case OperationType.IDLE:
                # if self._autoscroll_active or self._recording_active or self._autoscroll_screenshot_active:
                #     logger.debug("Something still active")
                #     self._restore_action_rows()
                #     self.set_status(self._persistent_status)
                #     self._apply_busy_state()
                # else:
                self._apply_idle_state()
                return

            case OperationType.SCREEN_RECORDING:
                self._recording_active = True
                self._cancel_btn.setText("Stop Recording")
                self._apply_busy_state()
                return

            case OperationType.STOP_SCREEN_RECORDING:
                self.set_status("")
                self._recording_active = False
                self._restore_action_rows()
                self._apply_busy_state()
                return

            case OperationType.AUTOSCROLL:
                self._autoscroll_btn.setText("Stop Autoscroll")
                self._autoscroll_btn.setStyleSheet(
                    "QPushButton {background-color: palette(bright-text); color: palette(window); }"
                )
                self._autoscroll_btn.clicked.disconnect()
                self._autoscroll_btn.clicked.connect(
                    lambda: self._on_combo_row_clicked(
                        self._autoscroll_btn, self._autoscroll_combo, OperationType.STOP_AUTOSCROLL
                    )
                )
                self._autoscroll_active = True
                self._apply_busy_state()
                return

            case OperationType.STOP_AUTOSCROLL:
                self._reset_autoscroll()
                if self._recording_active:
                    self.set_status(f"Recording {self._device.os} device")
                else:
                    self._persistent_status = ""
                    self.set_status("")
                self._apply_busy_state()
                return

            case OperationType.AUTOSCROLL_SCREENSHOT:
                self._autoscroll_screenshot_btn.setText("Stop Autoscroll Screenshot")
                self._autoscroll_screenshot_btn.setStyleSheet(
                    "QPushButton {background-color: palette(bright-text); color: palette(window); }"
                )
                self._autoscroll_screenshot_btn.clicked.disconnect()
                self._autoscroll_screenshot_btn.clicked.connect(
                    lambda: self._on_combo_row_clicked(
                        self._autoscroll_screenshot_btn,
                        self._autoscroll_screenshot_combo,
                        OperationType.STOP_AUTOSCROLL_SCREENSHOT,
                    )
                )
                self._autoscroll_screenshot_active = True
                self._persistent_status = self._status
                self._apply_busy_state()
                return

            case OperationType.STOP_AUTOSCROLL_SCREENSHOT:
                self._persistent_status = ""
                self.set_status("")
                self._reset_autoscroll_screenshot()
                self._apply_busy_state()
                return

        # Generic operation (backup, screenshot, etc.): disable everything and show cancel.
        for btn, bar in self._action_rows:
            btn.setDisabled(True)
        for btn, combo in self._combo_rows:
            btn.setDisabled(True)
            combo.setDisabled(True)
        if operation != OperationType.ENABLE_DEV_MODE:
            self._cancel_btn.show()
            self._cancel_btn.setEnabled(True)

    def _apply_busy_state(self) -> None:
        """Derive all button states from the active special-operation flags."""
        if not self._autoscroll_active and not self._recording_active and not self._autoscroll_screenshot_active:
            self._reset_btn_states()
            self._cancel_btn.hide()
            self._cancel_btn.setDisabled(True)
            return

        autoscroll_only = (
            self._autoscroll_active and not self._recording_active and not self._autoscroll_screenshot_active
        )

        for btn, bar in self._action_rows:
            is_screenshot = "Screenshot" in btn.text()
            is_recording_btn = btn.text() == "Start Screen Recording"
            connection_allows = self._device.connection_type != ConnectionType.NONE and not (
                self._device.connection_type == ConnectionType.PARTIAL and is_screenshot
            )
            btn.setEnabled(autoscroll_only and (is_screenshot or is_recording_btn) and connection_allows)

        for btn, combo in self._combo_rows:
            if btn is self._autoscroll_btn:
                btn.setEnabled(not self._autoscroll_screenshot_active)
                combo.setEnabled(not self._autoscroll_active and not self._autoscroll_screenshot_active)
            elif btn is self._autoscroll_screenshot_btn:
                btn.setEnabled(self._autoscroll_screenshot_active)
                combo.setDisabled(True)
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
        if status == "UXPLAY_STARTED_RECORDING":
            self._cancel_btn.hide()
            return

        self._status = status
        self._status_label.setText(status)

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
        self._heading_label.setText(self._device.device_name or self._device.identifier)
        self._details_label.setText(self._generate_details_label())

        full_connection = self._device.connection_type == ConnectionType.FULL
        partial_connection = self._device.connection_type == ConnectionType.PARTIAL

        if self._device.os == "iOS" and self._device.connection_type == ConnectionType.PARTIAL:
            self._enable_devmode_btn.show()
        else:
            self._enable_devmode_btn.hide()
            self._enable_devmode_bar.hide()

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
    def _restore_action_rows(self) -> None:
        for btn, bar in self._action_rows:
            btn.show()
            bar.hide()
            bar.setRange(0, 0)

    def _apply_idle_state(self) -> None:
        self._persistent_status = ""
        self.set_status("")
        self._recording_action = False
        self._reset_autoscroll()
        self._reset_autoscroll_screenshot()
        self._reset_btn_states()
        self._cancel_btn.hide()
        if self._device.os == "iOS" and self._device.connection_type == ConnectionType.PARTIAL:
            self._enable_devmode_btn.show()
            self._enable_devmode_bar.hide()
        else:
            self._enable_devmode_btn.hide()
            self._enable_devmode_bar.hide()

    def _reset_autoscroll(self) -> None:
        self._autoscroll_active = False
        self._autoscroll_btn.setText("Start Autoscroll")
        self._autoscroll_btn.setStyleSheet("")
        self._autoscroll_btn.clicked.disconnect()
        self._autoscroll_btn.clicked.connect(
            lambda: self._on_combo_row_clicked(self._autoscroll_btn, self._autoscroll_combo, OperationType.AUTOSCROLL)
        )
        self._autoscroll_combo.setEnabled(True)

    def _reset_autoscroll_screenshot(self) -> None:
        self._autoscroll_screenshot_active = False
        self._autoscroll_screenshot_btn.setText("Start Autoscroll Screenshot")
        self._autoscroll_screenshot_btn.setStyleSheet("")
        self._autoscroll_screenshot_btn.clicked.disconnect()
        self._autoscroll_screenshot_btn.clicked.connect(
            lambda: self._on_combo_row_clicked(
                self._autoscroll_screenshot_btn, self._autoscroll_screenshot_combo, OperationType.AUTOSCROLL_SCREENSHOT
            )
        )
        self._autoscroll_screenshot_combo.setEnabled(True)

    def _generate_details_label(self) -> str:
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

        return " | ".join(parts)

    def _on_action_row_clicked(self, btn: QPushButton, bar: QProgressBar, operation: OperationType) -> None:
        logger.debug(f"Pressed {btn.text()} with action {operation.name}")
        btn.hide()
        bar.setValue(0)
        bar.show()
        self.operation_requested.emit(operation, self._device)

    def _on_combo_row_clicked(
        self,
        btn: QPushButton,
        combo: QComboBox,
        operation: OperationType,
    ) -> None:
        logger.debug(f"Pressed {btn.text()} with action {operation.name} and selection {combo.currentText()}")
        combo.setDisabled(True) if combo.isEnabled() else combo.setEnabled(True)
        self.combo_operation_requested.emit(operation, self._device, combo.currentText())

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
