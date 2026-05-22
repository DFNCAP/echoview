from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject

from app.devices import android


class ConnectedDevicesController(QObject):
    def __init__(self) -> None:
        super().__init__()


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
    def backup(self, output_file: str | Path) -> str:
        """Take a backup and return the output path."""
        pass

    @abstractmethod
    def get_info(self) -> str:
        """Get device information as a formatted string."""
        pass


@dataclass
class AndroidDevice(Device):
    """Android device implementation."""

    def screenshot(self, output_file: Path) -> Path:
        """Take Android screenshot."""

        return android.screenshot(self.identifier, output_file)

    def backup(self, output_file: str | Path) -> str:

        return android.backup(self.identifier, output_file)

    def get_info(self) -> str:
        """Get Android device info."""
        return f"{self.os} - {self.device_name} ({self.serial})"


@dataclass
class iOSDevice(Device):
    """iOS device implementation."""

    def screenshot(self, output_directory: str) -> str:
        """Take iOS screenshot."""
        from app.devices.ios import screenshot as ios_screenshot

        return ios_screenshot(self.serial, output_directory)

    def backup(self, output_file: str) -> str:
        return output_file

    def get_info(self) -> str:
        """Get iOS device info."""
        return f"{self.os} - {self.device_name} ({self.serial})"
