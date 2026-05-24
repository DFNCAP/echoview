from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from app.devices.devices import Device


@dataclass
class iOSDevice(Device):
    """iOS device implementation."""

    def screenshot(self, output_directory: Path) -> Path:
        """Take iOS screenshot."""
        raise NotImplementedError(
            "Screenshot functionality is not available for iOS devices"
        )  # return ios.screenshot(self.serial, output_directory)

    def backup(self, output_file: Path) -> Path:
        raise NotImplementedError(
            "Backup functionality is not available for iOS devices"
        )

    def get_info(self) -> str:
        """Get iOS device info."""
        return f"{self.os} - {self.device_name} ({self.serial})"


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


def screenshot(udid: str, file_name: Path) -> Path:
    logger.info(f"Taking iOS screenshot of device {udid} to {file_name}")
    return file_name
