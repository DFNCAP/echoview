from PySide6.QtCore import QObject, Signal, Slot

from app.models.overview_model import OverviewModel
from app.views.overview_view import OverviewView


class OverviewController(QObject):
    output_directory_changed = Signal(str)
    job_number_changed = Signal(str)
    device_scan_requested = Signal()

    def __init__(self, view: OverviewView, model: OverviewModel) -> None:
        super().__init__()

        self._view = view
        self._model = model

        self._connect_internal_signals()

    def _connect_internal_signals(self) -> None:
        self._view.output_directory_changed.connect(self._on_output_directory_changed)
        self._view.job_number_changed.connect(self._on_job_number_changed)
        self._view.device_scan_requested.connect(self._on_device_scan_requested)

    @Slot(str)
    def _on_output_directory_changed(self, directory: str) -> None:
        self._model.output_directory = directory
        self.output_directory_changed.emit(self._model.output_directory)

    @Slot(str)
    def _on_job_number_changed(self, job_number: str) -> None:
        self._model.job_number = job_number
        self.output_directory_changed.emit(self._model.job_number)

    @Slot()
    def _on_device_scan_requested(self) -> None:
        self.device_scan_requested.emit()
