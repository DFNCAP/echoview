from pathlib import Path

from PySide6.QtCore import QObject, Signal

from app.controllers.overview_controller import OverviewController
from app.models.overview_model import OverviewModel


class FakeOverviewView(QObject):
    output_directory_changed = Signal(Path)
    job_number_changed = Signal(str)
    device_scan_requested = Signal()


def test_view_events_update_model_and_are_forwarded(qtbot, tmp_path: Path) -> None:
    view = FakeOverviewView()
    model = OverviewModel.__new__(OverviewModel)
    QObject.__init__(model)
    model._output_directory = Path()
    model._job_number = ""
    controller = OverviewController(view, model)

    with qtbot.waitSignal(controller.output_directory_changed) as directory_signal:
        view.output_directory_changed.emit(tmp_path)
    with qtbot.waitSignal(controller.job_number_changed) as job_signal:
        view.job_number_changed.emit("JOB-1")
    with qtbot.waitSignal(controller.device_scan_requested):
        view.device_scan_requested.emit()

    assert directory_signal.args == [tmp_path]
    assert job_signal.args == ["JOB-1"]
    assert model.output_directory == tmp_path
    assert model.job_number == "JOB-1"
