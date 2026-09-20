from app.devices.devices import OperationType
from app.views.devices_view import DevicesView


def test_scanning_indicator(qtbot) -> None:
    view = DevicesView()
    qtbot.addWidget(view)
    view.set_scanning(True)
    assert view._spinner.isVisibleTo(view)
    assert view._spinner_timer.isActive()
    view.set_scanning(False)
    assert not view._spinner.isVisible()
    assert not view._spinner_timer.isActive()


def test_add_update_remove_devices(qtbot, android_device) -> None:
    view = DevicesView()
    qtbot.addWidget(view)
    view.update_devices([android_device])
    widget = view.get_widget("android-1")
    assert widget is not None
    android_device.device_name = "Updated"
    view.update_devices([android_device])
    assert view.get_widget("android-1") is widget
    assert widget._heading_label.text() == "Updated"
    view.update_devices([])
    assert view.get_widget("android-1") is None


def test_targeted_updates(qtbot, android_device) -> None:
    view = DevicesView()
    qtbot.addWidget(view)
    view.update_devices([android_device])
    widget = view._device_widget_map["android-1"]
    view.set_status("android-1", "Working")
    view.set_progress("android-1", 2, 5)
    view.set_device_busy("android-1", OperationType.BACKUP)
    assert widget._status_label.text() == "Working"
    assert all(bar.maximum() == 5 for _, bar in widget._action_rows)
    assert widget._cancel_btn.isVisibleTo(widget)


def test_forwards_widget_signal(qtbot, android_device) -> None:
    view = DevicesView()
    qtbot.addWidget(view)
    view.update_devices([android_device])
    widget = view._device_widget_map["android-1"]
    with qtbot.waitSignal(view.operation_requested) as signal:
        widget.operation_requested.emit(OperationType.SCREENSHOT, android_device)
    assert signal.args == [OperationType.SCREENSHOT, android_device]
