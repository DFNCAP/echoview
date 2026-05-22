from loguru import logger

from app.devices.devices import iOSDevice


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


def screenshot(udid: str, file_name: str) -> str:
    logger.info(f"Taking iOS screenshot of device {udid} to {file_name}")
    return file_name
