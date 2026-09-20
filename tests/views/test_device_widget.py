import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from app.devices.devices import ConnectionType, OperationType
from app.views import device_widget


def _button(widget, text: str) -> QPushButton:
    return next(button for button in widget.findChildren(QPushButton) if button.text() == text)


def test_full_android_initial_state(qtbot, android_device) -> None:
    widget = device_widget.DeviceWidget(android_device)
    qtbot.addWidget(widget)
    assert widget._heading_label.text() == "Pixel"
    assert "Serial: android-1" in widget._details_label.text()
    assert not widget._warning_label.isVisibleTo(widget)
    assert not widget._enable_devmode_btn.isVisibleTo(widget)


def test_partial_ios_state(qtbot, ios_device) -> None:
    ios_device.connection_type = ConnectionType.PARTIAL
    widget = device_widget.DeviceWidget(ios_device)
    qtbot.addWidget(widget)
    widget.show()
    assert widget._enable_devmode_btn.isVisible()
    assert "developer mode" in widget._warning_label.text()
    assert not _button(widget, "Take Screenshot").isEnabled()


def test_exhibit_number_updates_device(qtbot, android_device) -> None:
    widget = device_widget.DeviceWidget(android_device)
    qtbot.addWidget(widget)
    widget._exhibit_number_input.setText("EX-1")
    widget._on_exhibit_number_changed()
    assert android_device.exhibit_id == "EX-1"


def test_action_emits_and_shows_progress(qtbot, android_device) -> None:
    widget = device_widget.DeviceWidget(android_device)
    qtbot.addWidget(widget)
    button = _button(widget, "Take Screenshot")
    row = next(row for row in widget._action_rows if row[0] is button)
    with qtbot.waitSignal(widget.operation_requested) as signal:
        qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert signal.args == [OperationType.SCREENSHOT, android_device]
    assert row[1].isVisibleTo(widget)


def test_combo_emits_direction(qtbot, android_device) -> None:
    widget = device_widget.DeviceWidget(android_device)
    qtbot.addWidget(widget)
    widget._autoscroll_combo.setCurrentText("left")
    with qtbot.waitSignal(widget.combo_operation_requested) as signal:
        qtbot.mouseClick(widget._autoscroll_btn, Qt.MouseButton.LeftButton)
    assert signal.args == [OperationType.AUTOSCROLL, android_device, "left"]


def test_progress_ranges(qtbot, android_device) -> None:
    widget = device_widget.DeviceWidget(android_device)
    qtbot.addWidget(widget)
    widget.set_progress(2, 5)
    assert all((bar.maximum(), bar.value()) == (5, 2) for _, bar in widget._action_rows)
    widget.set_progress(0, 0)
    assert all((bar.minimum(), bar.maximum()) == (0, 0) for _, bar in widget._action_rows)


def test_special_uxplay_statuses(qtbot, monkeypatch: pytest.MonkeyPatch, android_device) -> None:
    warning = []
    monkeypatch.setattr(device_widget, "show_warning", lambda *args: warning.append(args))
    widget = device_widget.DeviceWidget(android_device)
    qtbot.addWidget(widget)
    widget.set_status("UXPLAY_ENTER_PIN")
    assert warning == [("Enter Pin", "Enter pin '1234' on the device to continue")]


@pytest.mark.parametrize(
    ("operation", "cancel_text", "active_attribute"),
    [
        (OperationType.SCREEN_RECORDING, "Stop Recording", "_recording_active"),
        (OperationType.AUTOSCROLL, "Cancel", "_autoscroll_active"),
        (OperationType.AUTOSCROLL_SCREENSHOT, "Cancel", "_autoscroll_screenshot_active"),
    ],
)
def test_busy_state_transitions(qtbot, android_device, operation, cancel_text: str, active_attribute: str) -> None:
    widget = device_widget.DeviceWidget(android_device)
    qtbot.addWidget(widget)
    widget.set_busy(operation)
    assert getattr(widget, active_attribute) is True
    assert widget._cancel_btn.text() == cancel_text
    if operation is OperationType.SCREEN_RECORDING:
        widget.set_busy(OperationType.STOP_SCREEN_RECORDING)
    widget.set_busy(OperationType.IDLE)
    assert getattr(widget, active_attribute) is False
    assert not widget._cancel_btn.isVisibleTo(widget)


def test_cancel_signal(qtbot, android_device) -> None:
    widget = device_widget.DeviceWidget(android_device)
    qtbot.addWidget(widget)
    widget.set_busy(OperationType.BACKUP)
    with qtbot.waitSignal(widget.cancel_requested) as signal:
        qtbot.mouseClick(widget._cancel_btn, Qt.MouseButton.LeftButton)
    assert signal.args == [android_device]
    assert not widget._cancel_btn.isEnabled()
