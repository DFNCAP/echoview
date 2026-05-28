import threading
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from app.devices.devices import Device, StatusReporter


@dataclass
class iOSDevice(Device):
    """iOS device implementation."""

    def get_info(self) -> str:
        """Get iOS device info."""
        return f"{self.os} - {self.device_name} ({self.serial})"

    def backup(
        self,
        output_file: Path,
        reporter: StatusReporter | None = None,
        cancelled: threading.Event | None = None,
    ) -> Path:
        raise NotImplementedError(
            "Backup functionality is not available for iOS devices"
        )

    def screenshot(self, output_directory: Path) -> Path:
        raise NotImplementedError(
            "Screenshot functionality is not available for iOS devices"
        )

    def start_screen_recording(self, output_file: Path) -> None:
        raise NotImplementedError(
            "Screen recording functionality is not available for iOS devices"
        )

    def stop_screen_recording(self) -> None:
        pass


def get_connected_devices() -> list[iOSDevice]:
    logger.info("placeholder for ios")
    # Returns a list of iOSDevice
    device = iOSDevice(
        identifier="ios_iphone_14",
        serial="DEF456UVW012",
        device_name="iPhone 14 Pro",
        os="iOS",
        os_version="16.5",
        device_type="Phone",
        is_connected=True,
        width=1179,
        height=2556,
        connection_allowed=True,
    )
    return [device]
