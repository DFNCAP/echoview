import os
import platform
import shutil
import sys
import tarfile
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

import app.views.dialogue_box as dialogue
from app.utils.subprocess_helpers import popen, run


def get_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def platform_specific_open(path: str | Path) -> None:
    """
    Function to open a folder in the platform-specific file-explorer app
    or a file in the relevant system default application. On mac, if the path
    is a directory or an .app file, open the path in Finder using -R
    (i.e. treat .app as directory).

    :param path: path to open
    :type path: str | Path
    :param as_posix: if True, convert the path to a posix path regardless of the platform. This is useful for steam links.
    :type as_posix: bool
    """
    logger.info(f"USER ACTION: opening {path}")
    p = Path(path)
    path = str(path)
    if sys.platform == "darwin":
        logger.info(f"Opening {path} with subprocess open on MacOS")
        if p.is_dir() and p.suffix == ".app":
            popen(["open", path, "-R"])
        else:
            popen(["open", path])
    elif sys.platform == "win32":
        logger.info(f"Opening {path} with startfile on Windows")
        try:
            os.startfile(path)
        except OSError as e:
            # Handle cases where no default application is associated
            if e.winerror == -2147221003:  # Application not found
                logger.warning(f"No default application found for {path}, trying notepad")
                # Try to open with notepad as fallback
                try:
                    popen(["notepad.exe", path])
                except Exception as notepad_error:
                    logger.error(f"Failed to open with notepad: {notepad_error}")
                    dialogue.show_warning(
                        title="Failed to open file",
                        text="Could not open the file",
                        information=f"No default application is associated with this file type: {p.suffix}\n\nPlease manually associate an application with {p.suffix} files or open the file manually.",
                        details=str(e),
                    )
            else:
                # Re-raise other OSErrors
                raise
    elif sys.platform == "linux":
        logger.info(f"Opening {path} with xdg-open on Linux")
        popen(["xdg-open", path], env=dict(os.environ, LD_LIBRARY_PATH=""))
    else:
        logger.error("Attempting to open directory on an unknown system")


def extract_and_strip(archive: Path, destination: Path) -> None:
    """Extract archive to destination, stripping the top-level folder.

    This handles both .tar.gz and .zip archives, extracting their contents
    directly into the destination folder without the intermediate directory
    that archives typically contain.

    :param archive: Path to the archive file
    :type archive: Path
    :param destination: Directory where contents should be extracted
    :type destination: Path
    """
    destination.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Extract to temp directory
        if archive.suffix == ".zip":
            with zipfile.ZipFile(archive, "r") as zip_ref:
                zip_ref.extractall(temp_path)
        elif archive.suffixes == [".tar", ".gz"] or archive.name.endswith(".tar.gz"):
            with tarfile.open(archive, "r:gz") as tar_ref:
                tar_ref.extractall(temp_path)
        else:
            raise ValueError(f"Unsupported archive format: {archive}")

        # Move contents from the extracted subdirectory to destination
        extracted_dirs = [d for d in temp_path.iterdir() if d.is_dir()]
        if extracted_dirs:
            # Move contents from the first subdirectory
            for item in extracted_dirs[0].iterdir():
                target = destination / item.name
                if target.exists():
                    if target.is_dir():
                        shutil.rmtree(target)
                    else:
                        target.unlink()
                shutil.move(str(item), str(destination))


def extract(archive: Path, destination: Path) -> None:
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive, "r") as zip_ref:
            zip_ref.extractall(destination)
    elif archive.suffixes == [".tar", ".gz"] or archive.name.endswith(".tar.gz"):
        with tarfile.open(archive, "r:gz") as tar_ref:
            tar_ref.extractall(destination)
    else:
        raise ValueError(f"Unsupported archive format: {archive}")


def say(text: str) -> None:
    system = platform.system()
    if system == "Windows":
        script = f"Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak('{text}')"
        run(["powershell", "-Command", script], check=True)
    else:
        run(["espeak-ng", text], check=True)
