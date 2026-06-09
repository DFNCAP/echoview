import json
import platform
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from imagehash import average_hash
from PIL import Image

from app.devices.devices import ConnectionType, Device, StatusReporter
from app.devices.ios_product_types import product_type_to_model
from app.utils.app_info import AppInfo
from app.utils.generic import say
from app.utils.subprocess_helpers import popen, run


class DuplicateImageError(Exception):
    """Raised when duplicate images are detected during autoscroll screenshot."""


def _goios() -> str:
    """Get the path to the ADB executable."""
    return str(AppInfo().goios_path)


def _uxplay() -> str:
    return str(AppInfo().uxplay_path)


@dataclass
class iOSDevice(Device):
    """iOS device implementation."""

    def get_info(self) -> str:
        """Get iOS device info."""
        return f"{self.os} - {self.device_name} ({self.serial})"

    def backup(
        self,
        output_directory: Path,
        reporter: StatusReporter | None = None,
        cancelled: threading.Event | None = None,
    ) -> Path:
        raise NotImplementedError("Backup functionality is not available for iOS devices")

    def extract_contacts(self, output_file: Path) -> Path:
        raise NotImplementedError("Extract contacts functionality not implemented")

    def extract_device_info(self, output_directory: Path) -> None:
        installed_apps_proc = run(
            [_goios(), "--udid", self.identifier, "apps", "--list"], capture_output=True, text=True
        )
        if installed_apps_proc.stdout:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "installed_apps.txt"
            output_file.write_text(installed_apps_proc.stdout)

        system_apps_proc = run(
            [_goios(), "--udid", self.identifier, "apps", "--list", "--system"], capture_output=True, text=True
        )
        if system_apps_proc.stdout:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "system_apps.txt"
            output_file.write_text(system_apps_proc.stdout)

        info_proc = run(
            [_goios(), "--udid", self.identifier, "info"],
            capture_output=True,
            text=True,
        )
        if info_proc.stdout:
            output_directory.mkdir(parents=True, exist_ok=True)
            output_file = output_directory / "device_info.json"
            with output_file.open("w") as file:
                json.dump(json.loads(info_proc.stdout), file, indent=4)

    def extract_device_logs(
        self,
        output_directory: Path,
        reporter: StatusReporter | None = None,
        cancelled: threading.Event | None = None,
    ) -> None:
        raise NotImplementedError("Extract device logs functionality not implemented")

    def screenshot(self, output_file: Path) -> Path:
        return screenshot(self.identifier, output_file)

    def start_screen_recording(
        self,
        output_file: Path,
        reporter: StatusReporter | None = None,
    ) -> None:
        cmd = [
            _uxplay(),
            "-pin",
            "1234",
            "-mp4",
            str(output_file).replace("\\", "/"),
            "-n",
            f"echoview-{self.identifier}",
            "-nh",
        ]

        device_info = get_device_info(self.identifier)
        mac_address = device_info.get("EthernetAddress", "")
        if mac_address:
            cmd.extend(["-allow", mac_address.upper(), "-restrict"])

        output_file.parent.mkdir(parents=True, exist_ok=True)
        # self.recording_process = subprocess.Popen(cmd)

        self.recording_process = popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if self.recording_process.stdout and reporter:
            for line in self.recording_process.stdout:
                if "An Open-Source AirPlay mirroring and audio-streaming server" in line:
                    reporter.status_changed.emit("Initialising UxPlay")
                elif "Initialized server socket" in line:
                    reporter.status_changed.emit("Waiting for connection")
                elif "CLIENT MUST NOW ENTER PIN" in line:
                    reporter.status_changed.emit("UXPLAY_ENTER_PIN")
                elif "Begin streaming to GStreamer video pipeline" in line:
                    reporter.status_changed.emit("Recording")

        # self.recording_process.wait()
        # self.recording_process = None

    def stop_screen_recording(
        self,
        reporter: StatusReporter | None = None,
    ) -> None:
        if self.recording_process:
            pid = self.recording_process.pid

            if platform.system() == "Windows":
                run(
                    ["taskkill", "/pid", str(pid), "/T"],
                    capture_output=True,
                )

                try:
                    self.recording_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    run(
                        ["taskkill", "/f", "/pid", str(pid), "/T"],
                        capture_output=True,
                    )
            else:
                self.recording_process.terminate()
                try:
                    self.recording_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.recording_process.kill()

            self.recording_process = None

    def start_autoscroll(self, direction: str, cancelled: threading.Event) -> None:
        while not cancelled.is_set():
            scroll(direction)
            cancelled.wait(timeout=2.0)

    def autoscroll_screenshot(self, output_directory: Path, direction: str, cancelled: threading.Event) -> None:
        output_directory.mkdir(parents=True, exist_ok=True)

        screenshot_count = 0
        previous_hash = None
        duplicate_threshold = 5

        while not cancelled.is_set():
            # Take screenshot
            output_file = output_directory / f"screenshot_{screenshot_count:04d}.png"
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

            scroll(direction)
            cancelled.wait(timeout=2.0)


def get_connected_devices() -> list[iOSDevice]:
    proc = run([_goios(), "list"], capture_output=True, text=True)
    # logger.info(proc.stdout)
    data_dict = json.loads(proc.stdout)
    connected_devices: list[iOSDevice] = []
    for udid in data_dict["deviceList"]:
        device_info = get_device_info(udid)
        device = iOSDevice(identifier=udid, os="iOS")

        device.serial = device_info.get("SerialNumber", "")
        device.device_name = device_info.get("DeviceName", "")
        device.os_version = device_info.get("ProductVersion", "")
        device.device_type = product_type_to_model.get(device_info.get("ProductType", ""), "")
        if device_info:
            device.connection_type = ConnectionType.FULL if devmode_enabled(udid) else ConnectionType.PARTIAL
        connected_devices.append(device)

    return connected_devices


def get_device_info(udid: str) -> dict[Any, Any]:
    proc = run([_goios(), "info", "--udid", udid], capture_output=True, text=True)
    device_info: dict[Any, Any] = {}
    try:
        device_info = json.loads(proc.stdout)
    except Exception:
        pass

    return device_info


def screenshot(udid: str, output_file: Path) -> Path:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    proc = run(
        [
            _goios(),
            "--udid",
            udid,
            "screenshot",
            "--output",
            output_file,
        ],
        capture_output=True,
        text=True,
    )
    return output_file


def devmode_enabled(udid: str) -> bool:
    proc = run([_goios(), "devmode", "get", "--udid", udid], capture_output=True, text=True)
    devmode: dict[str, bool] = {}
    try:
        devmode = json.loads(proc.stdout)
    except Exception:
        return False

    return devmode.get("DeveloperModeEnabled", False)


def enable_devmode(udid: str) -> None:
    run(
        [_goios(), "devmode", "enable", "--enable-post-restart", "--udid", udid],
        capture_output=True,
        text=True,
    )


def dev_image_mounted(udid: str) -> bool:
    proc = run(
        [_goios(), "image", "list", "--udid", udid],
        capture_output=True,
        text=True,
    )
    if proc.stderr:
        for line in proc.stderr.splitlines():
            if "info" in line and "warning" not in line:
                output = json.loads(line)
                return output.get("msg", "none") != "none"

    return False


def mount_dev_image(udid: str) -> None:
    run(
        [_goios(), "image", "auto", "--udid", udid],
        capture_output=True,
        text=True,
    )
    time.sleep(1)


def version_to_int(version: str) -> int:
    parts = version.split(".")
    parts += ["0"] * (3 - len(parts))
    major, minor, patch = (int(p) for p in parts)
    return major * 10000 + minor * 100 + patch


def major_version(version: str) -> int:
    parts = version.split(".")
    major = int(parts[0])
    return major


def scroll(direction: str) -> None:
    command = f"scroll {direction}"
    say(command)


def start_ios_tunnel() -> subprocess.Popen[bytes]:
    return popen([_goios(), "tunnel", "start", "--userspace"])


def stop_ios_tunnel(proc: subprocess.Popen[bytes]) -> None:
    if proc:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
