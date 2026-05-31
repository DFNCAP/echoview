import subprocess
import threading
import platform
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from app.devices.devices import Device, StatusReporter
from app.utils.app_info import AppInfo


def _adb() -> str:
    """Get the path to the ADB executable."""
    return str(AppInfo().adb_path)


def _scrcpy() -> str:
    return str(AppInfo().scrcpy_path)


@dataclass
class AndroidDevice(Device):
    """Android device implementation."""

    def get_info(self) -> str:
        """Get Android device info."""
        return f"{self.os} - {self.device_name} ({self.serial})"

    def backup(
        self,
        output_directory: Path,
        reporter: StatusReporter | None = None,
        cancelled: threading.Event | None = None,
    ) -> Path:

        installed_packages = list_installed_packages(self.identifier)
        system_packages = list_system_packages(self.identifier)
        dirs_to_dump = ls(self.identifier, "/sdcard")

        items_to_dump = installed_packages + system_packages + dirs_to_dump
        for i, item in enumerate(items_to_dump, 1):
            if cancelled and cancelled.is_set():
                return Path()
            if reporter:
                reporter.progress_changed.emit(i, len(items_to_dump))
                reporter.status_changed.emit(f"Dumping {item}")

            if item in installed_packages:
                dump_apk(self.identifier, item, output_directory / "installed_packages")
            elif item in system_packages:
                dump_apk(self.identifier, item, output_directory / "system_packages")
            elif item in dirs_to_dump:
                dump(self.identifier, item, output_directory / "sdcard")

        return output_directory

    def start_screen_recording(self, output_file: Path) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        self.recording_process = subprocess.Popen(
            [
                _scrcpy(),
                "-s",
                self.identifier,
                "--window-title",
                self.identifier,
                "--record",
                str(output_file),
            ]
        )
        self.recording_process.wait()
        self.recording_process = None

    def stop_screen_recording(self) -> None:
        if self.recording_process:
            if platform.system() == "Windows":
                subprocess.run(
                    ["taskkill", "/pid", str(self.recording_process.pid)],
                    capture_output=True,
                )
            else:
                self.recording_process.terminate()

    def screenshot(self, output_file: Path) -> Path:
        """Take Android screenshot."""

        return screenshot(self.identifier, output_file)


def get_connected_devices() -> list[AndroidDevice]:
    proc = subprocess.run([_adb(), "devices"], capture_output=True, text=True)
    logger.info(proc.stdout)

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
        [_adb(), "-s", serial, "exec-out", "screencap", "-p"],
        capture_output=True,
    )
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_bytes(proc.stdout)

    return output_file


def backup(
    serial: str, output_file: Path, reporter: StatusReporter | None = None
) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(
        [
            _adb(),
            "-s",
            serial,
            "backup",
            "-all",
            "-nocompress",
            "-shared",
            "-system",
            "-apk",
            "-f",
            str(output_file),
        ],
        capture_output=True,
        text=True,
    )
    logger.info(f"Stdout: {proc.stdout}")
    logger.info(f"Stderr: {proc.stderr}")

    return output_file


def dump(
    serial: str,
    directory: str,
    output_directory: Path,
) -> None:
    logger.info(f"Dumping {directory} to {output_directory}")
    output_directory.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [_adb(), "-s", serial, "pull", directory, str(output_directory)],
        capture_output=True,
    )


def ls(serial: str, directory: str) -> list[str]:
    proc = subprocess.run(
        [_adb(), "-s", serial, "shell", "ls", "-1", directory],
        capture_output=True,
        text=True,
    )
    return [
        f"{directory}/{line}".strip()
        for line in proc.stdout.splitlines()
        if line.strip()
    ]


def list_all_packages(serial: str, flag: str = "") -> list[str]:
    all_packages = subprocess.run(
        [_adb(), "-s", serial, "shell", "pm", "list", "packages", flag],
        capture_output=True,
        text=True,
    ).stdout

    package_list = []
    for package in all_packages.splitlines():
        package_list.append(package.replace("package:", "").strip())

    logger.debug(f"Found {len(package_list)} packages")

    return package_list


def list_system_packages(serial: str) -> list[str]:
    output = subprocess.run(
        [_adb(), "-s", serial, "shell", "pm", "list", "packages", "-s"],
        capture_output=True,
        text=True,
    ).stdout

    system_packages = []
    for package in output.splitlines():
        system_packages.append(package.replace("package:", "").strip())

    logger.debug(f"Found {len(system_packages)} packages")

    return system_packages


def list_installed_packages(serial: str) -> list[str]:
    output = subprocess.run(
        [_adb(), "-s", serial, "shell", "pm", "list", "packages", "-3"],
        capture_output=True,
        text=True,
    ).stdout

    installed_packages = []
    for package in output.splitlines():
        installed_packages.append(package.replace("package:", "").strip())

    logger.debug(f"Found {len(installed_packages)} packages")

    return installed_packages


def dump_apk(serial: str, package: str, output_directory: Path) -> None:
    package_paths = subprocess.run(
        [_adb(), "-s", serial, "shell", "pm", "path", package],
        capture_output=True,
        text=True,
    ).stdout

    if not package_paths:
        logger.debug(f"No path found for package {package}, skipping...")
        return

    logger.debug(f"Dumping package {package}")
    out_dir = output_directory / package
    out_dir.mkdir(parents=True, exist_ok=True)

    for path in package_paths.splitlines():
        subprocess.run(
            [
                _adb(),
                "-s",
                serial,
                "pull",
                path.replace("package:", ""),
                str(out_dir),
            ],
            capture_output=True,
            text=True,
        )


def get_setting(serial: str, namespace: str, setting_name: str) -> str:
    proc = subprocess.run(
        [_adb(), "-s", serial, "shell", "settings", "get", namespace, setting_name],
        capture_output=True,
        text=True,
    )

    return proc.stdout.strip()


def get_property(serial: str, prop: str) -> str:
    proc = subprocess.run(
        [_adb(), "-s", serial, "shell", "getprop", prop],
        capture_output=True,
        text=True,
    )

    return proc.stdout.strip()


def kill_server() -> None:
    subprocess.run(
        [_adb(), "kill-server"],
    )
