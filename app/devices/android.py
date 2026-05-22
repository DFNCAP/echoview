import subprocess
from pathlib import Path

from loguru import logger

from app.devices.devices import AndroidDevice


def get_connected_devices() -> list[AndroidDevice]:
    proc = subprocess.run(["adb", "devices"], capture_output=True, text=True)

    connected_devices: list[AndroidDevice] = []
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) == 2:
            device = AndroidDevice(parts[0], serial=parts[0], os="Android")
            if parts[1] == "device":
                device.device_name = get_setting(parts[0], "global", "device_name")
                device.os_version = get_property(parts[0], "ro.build.version.release")
                device.device_type = get_property(parts[0], "ro.product.model")
                device.connection_allowed = True

            connected_devices.append(device)

    return connected_devices


def screenshot(serial: str, output_file: Path) -> Path:
    logger.info(f"Taking Android screenshot of device {serial} to {output_file}")
    proc = subprocess.run(
        ["adb", "-s", serial, "exec-out", "screencap", "-p"],
        capture_output=True,
    )
    output_file.write_bytes(proc.stdout)

    return output_file


def backup(serial: str, output_file: str | Path) -> str:
    subprocess.run(
        [
            "adb",
            "-s",
            serial,
            "backup",
            "-all",
            "-nocompress",
            "-shared",
            "-system",
            "-apk",
            "-f",
            output_file,
        ],
        capture_output=True,
    )

    return output_file


def get_setting(serial: str, namespace: str, setting_name: str) -> str:
    proc = subprocess.run(
        ["adb", "-s", serial, "shell", "settings", "get", namespace, setting_name],
        capture_output=True,
        text=True,
    )

    return proc.stdout


def get_property(serial: str, prop: str) -> str:
    proc = subprocess.run(
        ["adb", "-s", serial, "shell", "getprop", prop],
        capture_output=True,
        text=True,
    )

    return proc.stdout
