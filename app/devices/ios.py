import json
import platform
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from loguru import logger

from app.devices.devices import ConnectionType, Device, StatusReporter
from app.devices.ios_product_types import product_type_to_model
from app.utils.app_info import AppInfo


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
        raise NotImplementedError(
            "Backup functionality is not available for iOS devices"
        )

    def extract_contacts(self, output_file: Path) -> Path:
        raise NotImplementedError("Extract contacts functionality not implemented")

    def extract_device_info(self, output_directory: Path) -> None:
        raise NotImplementedError("Extract device info functionality not implemented")

    def extract_device_logs(
        self, output_directory: Path, reporter: StatusReporter | None = None
    ) -> None:
        raise NotImplementedError("Extract device logs functionality not implemented")

    def screenshot(self, output_file: Path) -> Path:
        raise NotImplementedError(
            "Screenshot functionality is not available for iOS devices"
        )

    def start_screen_recording(
        self,
        output_file: Path,
        reporter: StatusReporter | None = None,
    ) -> None:
        # raise NotImplementedError(
        #     "Screen recording functionality is not available for iOS devices"
        # )
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

        self.recording_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        if self.recording_process.stdout and reporter:
            for line in self.recording_process.stdout:
                logger.info(line.strip())
                if (
                    "An Open-Source AirPlay mirroring and audio-streaming server"
                    in line
                ):
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
                subprocess.run(
                    ["taskkill", "/pid", str(pid), "/T"],
                    capture_output=True,
                )

                try:
                    self.recording_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    subprocess.run(
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


def get_connected_devices() -> list[iOSDevice]:
    proc = subprocess.run([_goios(), "list"], capture_output=True, text=True)
    # logger.info(proc.stdout)
    data_dict = json.loads(proc.stdout)
    connected_devices: list[iOSDevice] = []
    for udid in data_dict["deviceList"]:
        device_info = get_device_info(udid)
        device = iOSDevice(identifier=udid, os="iOS")

        device.serial = device_info.get("SerialNumber", "")
        device.device_name = device_info.get("DeviceName", "")
        device.os_version = device_info.get("ProductVersion", "")
        device.device_type = product_type_to_model.get(
            device_info.get("ProductType", ""), ""
        )
        if device_info:
            device.connection_type = (
                ConnectionType.FULL if devmode_enabled(udid) else ConnectionType.PARTIAL
            )
        connected_devices.append(device)

    return connected_devices


def get_device_info(udid: str) -> dict[Any, Any]:
    proc = subprocess.run(
        [_goios(), "info", "--udid", udid], capture_output=True, text=True
    )
    device_info: dict[Any, Any] = {}
    try:
        device_info = json.loads(proc.stdout)
    except Exception:
        pass

    return device_info


def devmode_enabled(udid: str) -> bool:
    proc = subprocess.run(
        [_goios(), "devmode", "get", "--udid", udid], capture_output=True, text=True
    )
    devmode: dict[str, bool] = {}
    try:
        devmode = json.loads(proc.stdout)
    except Exception:
        return False

    return devmode.get("DeveloperModeEnabled", False)


def enable_devmode(udid: str) -> None:
    proc = subprocess.run(
        [_goios(), "devmode", "enable", "--enable-post-restart", "--udid", udid],
        capture_output=True,
        text=True,
    )
