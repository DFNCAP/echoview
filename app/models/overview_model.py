from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject

from app.utils.app_info import AppInfo


class OverviewModel(QObject):
    MIN_SIZE = 400
    MAX_SIZE = 1600
    DEFAULT_WIDTH = 900
    DEFAULT_HEIGHT = 600

    @staticmethod
    def validate_window_custom_size(width: int, height: int) -> tuple[int, int]:
        """Validate custom width and height, resetting to defaults if out of range."""
        if not (OverviewModel.MIN_SIZE <= width <= OverviewModel.MAX_SIZE):
            width = OverviewModel.DEFAULT_WIDTH
        if not (OverviewModel.MIN_SIZE <= height <= OverviewModel.MAX_SIZE):
            height = OverviewModel.DEFAULT_HEIGHT
        return width, height

    def __init__(self) -> None:
        super().__init__()

        self._settings_file = AppInfo().app_settings_file

        self._output_directory: Path = Path()
        self._job_number: str = ""

        self.load_settings()

    @property
    def output_directory(self) -> Path:
        """Return the currently selected output directory."""
        return self._output_directory

    @output_directory.setter
    def output_directory(self, directory: Path) -> None:
        """Set the output directory and emit a change signal if modified."""
        if self._output_directory != directory:
            self._output_directory = directory

    @property
    def job_number(self) -> str:
        """Return the current job number."""
        return self._job_number

    @job_number.setter
    def job_number(self, number: str) -> None:
        """Set the job number and emit a change signal if modified."""
        if self._job_number != number:
            self._job_number = number

    def load_settings(self) -> None:
        pass

    def save(self) -> None:
        pass
