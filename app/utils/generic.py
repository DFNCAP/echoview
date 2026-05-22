import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

import app.views.dialogue as dialogue


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
            subprocess.Popen(["open", path, "-R"])
        else:
            subprocess.Popen(["open", path])
    elif sys.platform == "win32":
        logger.info(f"Opening {path} with startfile on Windows")
        try:
            os.startfile(path)
        except OSError as e:
            # Handle cases where no default application is associated
            if e.winerror == -2147221003:  # Application not found
                logger.warning(
                    f"No default application found for {path}, trying notepad"
                )
                # Try to open with notepad as fallback
                try:
                    subprocess.Popen(["notepad.exe", path])
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
        subprocess.Popen(["xdg-open", path], env=dict(os.environ, LD_LIBRARY_PATH=""))
    else:
        logger.error("Attempting to open directory on an unknown system")
