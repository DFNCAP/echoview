import platform
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from imagehash import average_hash
from loguru import logger
from PIL import Image

from app.devices.devices import ConnectionType, Device, NullReporter, StatusReporter
from app.utils.app_info import AppInfo
from app.utils.generic import get_timestamp
from app.utils.subprocess_helpers import popen, run


class NoContactsFoundError(Exception):
    """Raised when no contacts are found on the device."""


class DuplicateImageError(Exception):
    """Raised when duplicate images are detected during autoscroll screenshot."""


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
        reporter: StatusReporter | NullReporter = NullReporter(),
        cancelled: threading.Event | None = None,
    ) -> Path:

        installed_packages = list_installed_packages(self.identifier)
        system_packages = list_system_packages(self.identifier)
        dirs_to_dump = ls(self.identifier, "/sdcard")

        items_to_dump = installed_packages + system_packages + dirs_to_dump
        for i, item in enumerate(items_to_dump, 1):
            if cancelled and cancelled.is_set():
                return Path()
            reporter.progress_changed.emit(self.identifier, i, len(items_to_dump))
            reporter.status_changed.emit(self.identifier, f"Dumping {item}")

            if item in installed_packages:
                dump_apk(self.identifier, item, output_directory / "installed_packages")
            elif item in system_packages:
                dump_apk(self.identifier, item, output_directory / "system_packages")
            elif item in dirs_to_dump:
                dump(self.identifier, item, output_directory / "sdcard")

        return output_directory

    def extract_contacts(self, output_file: Path) -> Path:
        contacts = get_contacts(self.identifier)
        if contacts:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with output_file.open(mode="w", encoding="utf-8") as file:
                for entry in contacts:
                    file.write(f"{entry[0]} : {entry[1]}\n")

        else:
            raise NoContactsFoundError("No contacts found on the device")
        return output_file

    def extract_device_info(
        self,
        output_directory: Path,
        reporter: StatusReporter | NullReporter = NullReporter(),
        cancelled: threading.Event | None = None,
    ) -> None:
        reporter.status_changed.emit(self.identifier, "Dumping props")
        reporter.progress_changed.emit(self.identifier, 0, 4)

        getprop_proc = run([_adb(), "-s", self.identifier, "shell", "getprop"], capture_output=True)
        if getprop_proc.stdout:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "getprop_raw.txt"
            output_file.write_bytes(getprop_proc.stdout)

        reporter.status_changed.emit(self.identifier, "Dumping system settings")
        reporter.progress_changed.emit(self.identifier, 1, 4)
        system_settings_proc = run(
            [_adb(), "-s", self.identifier, "shell", "settings", "list", "system"],
            capture_output=True,
        )
        if system_settings_proc.stdout:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "system_settings_raw.txt"
            output_file.write_bytes(system_settings_proc.stdout)

        reporter.status_changed.emit(self.identifier, "Dumping secure settings")
        reporter.progress_changed.emit(self.identifier, 2, 4)
        secure_settings_proc = run(
            [_adb(), "-s", self.identifier, "shell", "settings", "list", "secure"],
            capture_output=True,
        )
        if secure_settings_proc.stdout:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "secure_settings_raw.txt"
            output_file.write_bytes(secure_settings_proc.stdout)

        reporter.status_changed.emit(self.identifier, "Dumping global settings")
        reporter.progress_changed.emit(self.identifier, 3, 4)
        global_settings_proc = run(
            [_adb(), "-s", self.identifier, "shell", "settings", "list", "global"],
            capture_output=True,
        )
        if global_settings_proc.stdout:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "global_settings_raw.txt"
            output_file.write_bytes(global_settings_proc.stdout)

        reporter.status_changed.emit(self.identifier, "Dumping app list")
        reporter.progress_changed.emit(self.identifier, 4, 4)
        installed_packages = list_installed_packages(self.identifier)
        if installed_packages:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "third_party_apps.log"
            output_file.write_text("\n".join(installed_packages), encoding="utf8")

        system_packages = list_system_packages(self.identifier)
        if system_packages:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "system_apps.log"
            output_file.write_text("\n".join(system_packages), encoding="utf8")

    def extract_device_logs(
        self,
        output_directory: Path,
        reporter: StatusReporter | NullReporter = NullReporter(),
        cancelled: threading.Event | None = None,
    ) -> None:

        reporter.progress_changed.emit(self.identifier, 0, 4)
        reporter.status_changed.emit(self.identifier, "Dumping system log")

        dumpsys_proc = popen(
            [_adb(), "-s", self.identifier, "shell", "dumpsys"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        while dumpsys_proc.poll() is None:
            if cancelled and cancelled.is_set():
                dumpsys_proc.kill()
                dumpsys_proc.wait()
                return
            time.sleep(0.05)
        dumpsys_stdout = dumpsys_proc.stdout.read() if dumpsys_proc.stdout else b""
        if dumpsys_stdout:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "dumpsys.log"
            output_file.write_bytes(dumpsys_stdout)

        if cancelled and cancelled.is_set():
            return

        reporter.progress_changed.emit(self.identifier, 1, 4)
        reporter.status_changed.emit(self.identifier, "Generating bug report archive")
        output_directory.mkdir(parents=True, exist_ok=True)
        output_file = output_directory / "bugreport-archive.zip"
        bugreport_proc = popen([_adb(), "-s", self.identifier, "bugreport", output_file])
        while bugreport_proc.poll() is None:
            if cancelled and cancelled.is_set():
                bugreport_proc.kill()
                bugreport_proc.wait()
                return
            time.sleep(0.05)
        if cancelled and cancelled.is_set():
            return

        reporter.progress_changed.emit(self.identifier, 2, 4)
        reporter.status_changed.emit(self.identifier, "Dumping logcat stats")

        logcat_stats_proc = run(
            [_adb(), "-s", self.identifier, "shell", "logcat", "-S", "-b", "all"],
            capture_output=True,
        )

        if logcat_stats_proc.stdout:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "logcat_stats.log"
            output_file.write_bytes(logcat_stats_proc.stdout)
        if cancelled and cancelled.is_set():
            return

        reporter.progress_changed.emit(self.identifier, 3, 4)
        reporter.status_changed.emit(self.identifier, "Dumping logcat logs")

        logcat_logs_proc = run(
            [_adb(), "-s", self.identifier, "shell", "logcat", "-d", "-b", "all"],
            capture_output=True,
        )
        if logcat_logs_proc.stdout:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "logcat_log.log"
            output_file.write_bytes(logcat_logs_proc.stdout)
        if cancelled and cancelled.is_set():
            return

        reporter.progress_changed.emit(self.identifier, 4, 4)
        reporter.status_changed.emit(self.identifier, "Finalising")

    def start_screen_recording(
        self,
        output_file: Path,
        reporter: StatusReporter | NullReporter = NullReporter(),
    ) -> None:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        reporter.status_changed.emit(self.identifier, f"Recording {self.os} device")

        self.recording_process = popen(
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

    def stop_screen_recording(
        self,
        reporter: StatusReporter | NullReporter = NullReporter(),
    ) -> None:
        if self.recording_process:
            if platform.system() == "Windows":
                run(
                    ["taskkill", "/pid", str(self.recording_process.pid)],
                    capture_output=True,
                )
            else:
                self.recording_process.terminate()

    def screenshot(
        self,
        output_file: Path,
        reporter: StatusReporter | NullReporter = NullReporter(),
    ) -> Path:

        return screenshot(self.identifier, output_file)

    def start_autoscroll(
        self,
        direction: str,
        cancelled: threading.Event,
        reporter: StatusReporter | NullReporter = NullReporter(),
    ) -> None:
        while not cancelled.is_set():
            reporter.status_changed.emit(self.identifier, f"Scrolling {direction}")
            scroll(
                self.identifier,
                direction,
                self.width or 1080,
                self.height or 1920,
            )
            reporter.status_changed.emit(self.identifier, "Waiting")
            cancelled.wait(timeout=2.0)

    def autoscroll_screenshot(
        self,
        output_directory: Path,
        direction: str,
        cancelled: threading.Event,
        reporter: StatusReporter | NullReporter = NullReporter(),
    ) -> None:

        output_directory.mkdir(parents=True, exist_ok=True)

        screenshot_count = 0
        previous_hash = None
        duplicate_threshold = 5

        while not cancelled.is_set():
            reporter.status_changed.emit(self.identifier, "Taking screenshot")
            output_file = output_directory / f"screenshot_{get_timestamp()}.png"

            screenshot(self.identifier, output_file)
            screenshot_count += 1

            try:
                current_hash = average_hash(Image.open(output_file))
                if previous_hash is not None:
                    hash_diff = current_hash - previous_hash
                    if hash_diff < duplicate_threshold:
                        output_file.unlink()
                        raise DuplicateImageError(
                            f"Duplicate images detected (hash difference: {hash_diff}). "
                            "Autoscroll screenshot terminated."
                        )
                previous_hash = current_hash
            except Exception:
                raise

            # Scroll
            reporter.status_changed.emit(self.identifier, f"Scrolling {direction}")
            scroll(
                self.identifier,
                direction,
                self.width,
                self.height,
            )

            # Wait 2 seconds
            cancelled.wait(timeout=2.0)


def get_connected_devices() -> list[AndroidDevice]:
    proc = run([_adb(), "devices"], capture_output=True, text=True)

    connected_devices: list[AndroidDevice] = []
    for line in proc.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) == 2:
            device = AndroidDevice(parts[0], serial=parts[0], os="Android")
            if parts[1] == "device":
                device.device_name = get_setting(device.identifier, "global", "device_name")
                device.os_version = get_property(device.identifier, "ro.build.version.release")
                device.device_type = get_property(device.identifier, "ro.product.model")
                device.width, device.height = get_window_size(device.identifier)

                device.connection_type = ConnectionType.FULL

            connected_devices.append(device)

    return connected_devices


def get_contacts(serial: str) -> list[tuple[str, str]]:
    # proc = run(
    #     [
    #         _adb(),
    #         "-s",
    #         serial,
    #         "shell",
    #         "content",
    #         "query",
    #         "--uri",
    #         "content://contacts/phones",
    #         "--projection",
    #         "name:number",
    #     ],
    #     capture_output=True,
    #     text=True,
    # )

    # contacts: list[tuple[str, str]] = []
    # if "No result found." in proc.stdout:
    #     return contacts

    # for line in proc.stdout.splitlines():
    #     row = line.strip().split(": ", 1)[-1].split(" ", 1)[-1]
    #     name = row.split(", ", 1)[0].removeprefix("name=")
    #     number = row.split(", ", 1)[-1].removeprefix("number=")
    #     contacts.append((name, number))

    proc = run(
        [
            _adb(),
            "-s",
            serial,
            "shell",
            "content",
            "query",
            "--uri",
            "content://com.android.contacts/data",
            "--projection",
            "display_name:data1",
        ],
        capture_output=True,
        text=True,
    )

    contacts: list[tuple[str, str]] = []
    if "No result found." in proc.stdout:
        return contacts

    for line in proc.stdout.splitlines():
        row = line.strip().split(": ", 1)[-1].split(" ", 1)[-1]
        name = row.split(", ", 1)[0].removeprefix("display_name=")
        number = row.split(", ", 1)[-1].removeprefix("data1=")
        if name != number:
            contacts.append((name, number))

    return contacts


def screenshot(serial: str, output_file: Path) -> Path:
    proc = run(
        [_adb(), "-s", serial, "exec-out", "screencap", "-p"],
        capture_output=True,
    )
    if proc.stdout:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_bytes(proc.stdout)

    return output_file


def backup(serial: str, output_file: Path, reporter: StatusReporter | None = None) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)

    run(
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

    return output_file


def dump(
    serial: str,
    directory: str,
    output_directory: Path,
) -> None:
    logger.info(f"Dumping {directory} to {output_directory}")
    output_directory.mkdir(parents=True, exist_ok=True)
    run(
        [_adb(), "-s", serial, "pull", directory, str(output_directory)],
        capture_output=True,
    )


def ls(serial: str, directory: str) -> list[str]:
    proc = run(
        [_adb(), "-s", serial, "shell", "ls", "-1", directory],
        capture_output=True,
        text=True,
    )
    return [f"{directory}/{line}".strip() for line in proc.stdout.splitlines() if line.strip()]


def list_all_packages(serial: str, flag: str = "") -> list[str]:
    all_packages = run(
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
    output = run(
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
    output = run(
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
    package_paths = run(
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
        run(
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
    proc = run(
        [_adb(), "-s", serial, "shell", "settings", "get", namespace, setting_name],
        capture_output=True,
        text=True,
    )

    return proc.stdout.strip()


def get_property(serial: str, prop: str) -> str:
    proc = run(
        [_adb(), "-s", serial, "shell", "getprop", prop],
        capture_output=True,
        text=True,
    )

    return proc.stdout.strip()


def get_window_size(serial: str) -> tuple[int, int]:
    width, height = 0, 0
    proc = run(
        [_adb(), "-s", serial, "shell", "wm", "size"],
        capture_output=True,
        text=True,
    )
    if proc.stdout:
        dimensions = proc.stdout.split(": ")[1].split("x")
        width = int(dimensions[0])
        height = int(dimensions[1])

    return width, height


def scroll(serial: str, direction: str, width: int, height: int) -> bool:
    cx, cy = width // 2, height // 2

    match direction:
        case "up":
            start, end = (cx, cy // 2), (cx, height)
        case "down":
            start, end = (cx, cy + cy // 2), (cx, 0)
        case "left":
            start, end = (cx // 2, cy), (width, cy)
        case "right":
            start, end = (cx + cx // 2, cy), (0, cy)
        case _:
            return False

    x_start, y_start = start
    x_end, y_end = end

    proc = run(
        [
            _adb(),
            "-s",
            serial,
            "shell",
            "input",
            "swipe",
            str(x_start),
            str(y_start),
            str(x_end),
            str(y_end),
            "800",
        ],
        capture_output=True,
        text=True,
    )

    return not proc.stderr


def kill_server() -> None:
    run([_adb(), "kill-server"])
