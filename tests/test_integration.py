import pytest

from app.models.devices_model import DevicesModel
from app.views.devices_view import DevicesView


@pytest.mark.integration
def test_model_device_change_reconciles_view(qtbot, android_device) -> None:
    model = DevicesModel()
    view = DevicesView()
    qtbot.addWidget(view)
    model.devices_changed.connect(view.update_devices)

    model.devices = [android_device]
    assert view.get_widget(android_device.identifier) is not None

    model.devices = []
    assert view.get_widget(android_device.identifier) is None
