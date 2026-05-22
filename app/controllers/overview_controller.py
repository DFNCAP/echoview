from loguru import logger
from PySide6.QtCore import QObject, Signal, Slot

from app.models.overview_model import OverviewModel
from app.views.overview_view import OverviewView


class OverviewController(QObject):
    # Signal for device scan requests
    device_scan_requested = Signal()

    def __init__(self, view: OverviewView, model: OverviewModel) -> None:
        super().__init__()

        self._view = view
        self._model = model

        self._view.output_directory_changed.connect(self._on_output_directory_changed)
        self._model.output_directory_updated.connect(self._view.set_directory_label)

        self._view.job_number_changed.connect(self._on_job_number_changed)
        self._view.device_scan_requested.connect(self._on_device_scan_requested)

    @Slot(str)
    def _on_output_directory_changed(self, directory: str) -> None:
        self._model.output_directory = directory

    @Slot(str)
    def _on_job_number_changed(self, job_number: str) -> None:
        logger.debug("Job number updated")
        self._model.job_number = job_number

    @Slot()
    def _on_device_scan_requested(self) -> None:
        logger.info("Device scan requested from OverviewController")
        self.device_scan_requested.emit()
