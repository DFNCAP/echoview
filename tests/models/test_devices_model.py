from pathlib import Path

from app.models.devices_model import DevicesModel


def test_defaults_and_properties(qtbot, android_device) -> None:
    model = DevicesModel()

    assert model.devices == []
    assert model.output_directory == Path()
    assert model.job_number == ""

    with qtbot.waitSignal(model.devices_changed, timeout=1000) as blocker:
        model.devices = [android_device]

    assert blocker.args == [[android_device]]
    model.output_directory = Path("/output")
    model.job_number = "JOB-1"
    assert model.output_directory == Path("/output")
    assert model.job_number == "JOB-1"


def test_devices_signal_only_emitted_for_change(qtbot, android_device) -> None:
    model = DevicesModel()
    devices = [android_device]
    model.devices = devices
    received = []
    model.devices_changed.connect(received.append)

    model.devices = devices

    assert received == []
