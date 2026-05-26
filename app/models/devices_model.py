from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal

from app.devices.devices import Device


class DevicesModel(QObject):
    devices_changed = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._devices: list[Device] = []
        self._output_directory: Path = Path()
        self._job_number: str = ""

    @property
    def devices(self) -> list[Device]:
        return self._devices

    @devices.setter
    def devices(self, devices: list[Device]) -> None:
        if self._devices != devices:
            self._devices = devices
            self.devices_changed.emit(self._devices)

    @property
    def output_directory(self) -> Path:
        return self._output_directory

    @output_directory.setter
    def output_directory(self, directory: Path) -> None:
        if self._output_directory != directory:
            logger.info(f"Output directory changed to {directory}")
            self._output_directory = directory

    @property
    def job_number(self) -> str:
        return self._job_number

    @job_number.setter
    def job_number(self, job_number: str) -> None:
        if self._job_number != job_number:
            logger.info(f"Job number changed to {job_number}")
            self._job_number = job_number
