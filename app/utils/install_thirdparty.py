import platform
import subprocess
import zipfile
from pathlib import Path

from loguru import logger

from app.utils.app_info import AppInfo
from app.utils.generic import extract, extract_and_strip

SYSTEM = platform.system()


def unpack_scrcpy() -> bool:
    source_dir = AppInfo().application_folder / "scrcpy"

    # Check if already extracted
    if SYSTEM == "Linux":
        archive_pattern = "scrcpy-linux*.tar.gz"
        required_files = ["adb", "scrcpy"]
    elif SYSTEM == "Windows":
        archive_pattern = "scrcpy-win64*.zip"
        required_files = ["adb.exe", "scrcpy.exe"]
    else:
        logger.warning(f"Unsupported OS: {SYSTEM}")
        return False

    # Check if required files already exist
    if all((source_dir / f).exists() for f in required_files):
        logger.debug(f"scrcpy already extracted at {source_dir}")
        return True

    archives = list(source_dir.glob(archive_pattern))
    if not archives:
        logger.warning(f"No {archive_pattern} files found in {source_dir}")
        return False

    archive = archives[0]
    destination = source_dir

    extract_and_strip(archive, destination)

    return True


def unpack_goios() -> bool:
    source_dir = AppInfo().application_folder / "go-ios"
    archive_pattern = "go-ios*.zip"

    if SYSTEM == "Linux":
        archive_pattern = "go-ios-linux*.zip"
        required_files = ["ios-amd64"]
    elif SYSTEM == "Windows":
        archive_pattern = "go-ios-win*.zip"
        required_files = ["ios.exe"]
    else:
        logger.warning(f"Unsupported OS: {SYSTEM}")
        return False

    if all((source_dir / f).exists() for f in required_files):
        logger.debug(f"go-ios already extracted at {source_dir}")
        return True

    archives = list(source_dir.glob(archive_pattern))
    if not archives:
        logger.warning(f"No {archive_pattern} files found in {source_dir}")
        return False

    archive = archives[0]
    destination = source_dir
    with zipfile.ZipFile(archive, "r") as zip_ref:
        zip_ref.extractall(destination)

    return True


def unpack_wintun() -> bool:
    if SYSTEM == "Linux":
        return True

    destination = AppInfo().application_folder / "go-ios" / "wintun.dll"

    if destination.exists():
        logger.debug(f"wintun already extracted at {destination}")
        return True

    source_dir = AppInfo().application_folder / "wintun"
    archive_pattern = "wintun*.zip"
    archives = list(source_dir.glob(archive_pattern))
    if not archives:
        logger.warning(f"No {archive_pattern} files found in {source_dir}")
        return False

    archive = archives[0]
    with zipfile.ZipFile(archive, "r") as zip_ref:
        data = zip_ref.read("wintun/bin/amd64/wintun.dll")

    destination.write_bytes(data)

    return True


def unpack_uxplay() -> bool:
    source_dir = AppInfo().application_folder / "uxplay"

    # Check if already extracted
    if SYSTEM == "Linux":
        archive_pattern = "uxplay-linux*.tar.gz"
        required_files = ["uxplay"]
    elif SYSTEM == "Windows":
        archive_pattern = "uxplay-win64*.zip"
        required_files = ["uxplay.exe"]
    else:
        logger.warning(f"Unsupported OS: {SYSTEM}")
        return False

    # Check if required files already exist
    if all((source_dir / "bin" / f).exists() for f in required_files):
        logger.debug(f"uxplay already extracted at {source_dir}")
        return True

    archives = list(source_dir.glob(archive_pattern))
    if not archives:
        logger.warning(f"No {archive_pattern} files found in {source_dir}")
        return False

    archive = archives[0]

    extract(archive, source_dir)

    return True


def install_bonjour() -> bool:
    if is_installed("Bonjour"):
        return True

    msi_path = AppInfo().application_folder / "apple" / "Bonjour64.msi"
    return install_msi(msi_path)


def install_AppleMobileDeviceSupport() -> bool:
    if is_installed("Apple Mobile Device Support"):
        return True

    msi_path = AppInfo().application_folder / "apple" / "AppleMobileDeviceSupport64.msi"
    return install_msi(msi_path)


def is_installed(name: str) -> bool:
    import winreg

    keys = [
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall",
        r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ]
    for key_path in keys:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, subkey_name) as subkey:
                            display_name, _ = winreg.QueryValueEx(subkey, "DisplayName")
                            if name.lower() in display_name.lower():
                                logger.debug(f"{name} is already installed")
                                return True
                    except OSError:
                        continue
        except OSError:
            continue
    return False


def install_msi(msi_path: Path) -> bool:
    try:
        logger.debug(f"Installing {msi_path}")
        subprocess.run(["msiexec", "/i", msi_path, "/passive", "/norestart"], check=True)
    except subprocess.CalledProcessError as e:
        if e.returncode == 5:  # Access denied
            return _elevate_and_install(msi_path)
        else:
            logger.error(f"Failed to install {msi_path}")
            return False
    return True


def _elevate_and_install(msi_path: Path) -> bool:
    import ctypes

    logger.debug(f"Installing {msi_path} with elevated privileges")

    result = ctypes.windll.shell32.ShellExecuteW(
        None,  # parent window handle
        "runas",  # verb — triggers UAC prompt
        "msiexec",  # executable
        f'/i "{msi_path}" /passive /norestart',  # parameters
        None,  # working directory
        1,  # show window
    )
    if result <= 32:
        return False

    return True
