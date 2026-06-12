import subprocess
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, IntEnum, auto
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal


class StatusReporter(QObject):
    status_changed = Signal(str, str)
    progress_changed = Signal(str, int, int)


class ConnectionType(Enum):
    NONE = 0
    PARTIAL = 1
    FULL = 2


class OperationType(IntEnum):
    IDLE = auto()
    DEVICE_SCAN = auto()
    BACKUP = auto()
    EXTRACT_CONTACTS = auto()
    EXTRACT_DEVICE_INFO = auto()
    EXTRACT_DEVICE_LOGS = auto()
    SCREEN_RECORDING = auto()
    STOP_SCREEN_RECORDING = auto()
    SCREENSHOT = auto()

    AUTOSCROLL = auto()
    STOP_AUTOSCROLL = auto()
    AUTOSCROLL_SCREENSHOT = auto()
    STOP_AUTOSCROLL_SCREENSHOT = auto()

    IOS_TUNNEL = auto()
    ENABLE_DEV_MODE = auto()


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
    connection_type: ConnectionType = ConnectionType.NONE
    exhibit_id: str = ""

    recording_process: subprocess.Popen[Any] | None = None

    @abstractmethod
    def backup(
        self,
        output_directory: Path,
        reporter: StatusReporter | None = None,
        cancelled: threading.Event | None = None,
    ) -> Path:
        """Take a backup and return the output path."""
        pass

    @abstractmethod
    def extract_contacts(self, output_file: Path) -> Path:
        """Take a screenshot and return the output path."""
        pass

    @abstractmethod
    def extract_device_info(
        self,
        output_directory: Path,
        reporter: StatusReporter | None = None,
        cancelled: threading.Event | None = None,
    ) -> None:
        """Take a screenshot and return the output path."""
        pass

    @abstractmethod
    def extract_device_logs(
        self,
        output_directory: Path,
        reporter: StatusReporter | None = None,
        cancelled: threading.Event | None = None,
    ) -> None:
        """Take a screenshot and return the output path."""
        pass

    @abstractmethod
    def start_screen_recording(
        self,
        output_file: Path,
        reporter: StatusReporter | None = None,
    ) -> None:
        pass

    @abstractmethod
    def stop_screen_recording(
        self,
        reporter: StatusReporter | None = None,
    ) -> None:
        pass

    @abstractmethod
    def screenshot(self, output_file: Path) -> Path:
        """Take a screenshot and return the output path."""
        pass

    @abstractmethod
    def start_autoscroll(self, direction: str, cancelled: threading.Event) -> None:
        """Start autoscrolling in the specified direction."""
        pass

    @abstractmethod
    def autoscroll_screenshot(self, output_directory: Path, direction: str, cancelled: threading.Event) -> None:
        """Take screenshots while autoscrolling in the specified direction."""
        pass

    @abstractmethod
    def get_info(self) -> str:
        """Get device information as a formatted string."""
        pass
