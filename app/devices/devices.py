import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal


class StatusReporter(QObject):
    status_changed = Signal(str)
    progress_changed = Signal(int, int)


@dataclass
class Device(ABC):
    identifier: str
    serial: str = ""
    device_name: str = ""
    os: str = ""
    os_version: str = ""
    device_type: str = ""
    is_connected: bool = False
    width: int = 0
    height: int = 0
    connection_allowed: bool = False

    @abstractmethod
    def screenshot(self, output_file: Path) -> Path:
        """Take a screenshot and return the output path."""
        pass

    @abstractmethod
    def backup(
        self,
        output_file: Path,
        reporter: StatusReporter | None = None,
        cancelled: threading.Event | None = None,
    ) -> Path:
        """Take a backup and return the output path."""
        pass

    @abstractmethod
    def get_info(self) -> str:
        """Get device information as a formatted string."""
        pass
