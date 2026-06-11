#!/usr/bin/env python3
# Compilation mode
# nuitka-project: --output-filename=EchoView
# nuitka-project: --mode=standalone
# nuitka-project: --output-dir={MAIN_DIRECTORY}/../build/
# nuitka-project: --nofollow-import-to=scipy
# nuitka-project: --windows-console-mode=attach

# Plugins
# nuitka-project: --enable-plugin=pyside6

# OS-Specific
# nuitka-project-if: {OS} == "Darwin":
#   nuitka-project: --mode=app
# nuitka-project-else:
#   nuitka-project: --mode=standalone

# Version info
# nuitka-project-if: os.path.exists("{MAIN_DIRECTORY}/../version.xml"):
#   nuitka-project: --include-data-file={MAIN_DIRECTORY}/../version.xml=version.xml

# scrcpy
# nuitka-project-if: {OS} == "Linux":
#   nuitka-project: --include-data-files={MAIN_DIRECTORY}/../scrcpy/scrcpy-linux*.tar.gz=scrcpy/
# nuitka-project-if: {OS} == "Windows":
#   nuitka-project: --include-data-files={MAIN_DIRECTORY}/../scrcpy/scrcpy-win64*.zip=scrcpy/
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/../scrcpy/LICENSE=scrcpy/

# go-ios
# nuitka-project-if: {OS} == "Linux":
#   nuitka-project: --include-data-files={MAIN_DIRECTORY}/../go-ios/go-ios-linux*.zip=go-ios/
# nuitka-project-if: {OS} == "Windows":
#   nuitka-project: --include-data-files={MAIN_DIRECTORY}/../go-ios/go-ios-win*.zip=go-ios/
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/../go-ios/LICENSE=go-ios/

# wintun
# nuitka-project-if: {OS} == "Windows":
#   nuitka-project: --include-data-files={MAIN_DIRECTORY}/../wintun/wintun*.zip=wintun/
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/../wintun/LICENSE.txt=wintun/

# uxplay
# nuitka-project-if: {OS} == "Linux":
#   nuitka-project: --include-data-files={MAIN_DIRECTORY}/../uxplay/uxplay-linux*.tar.gz=uxplay/
# nuitka-project-if: {OS} == "Windows":
#   nuitka-project: --include-data-files={MAIN_DIRECTORY}/../uxplay/uxplay-win64*.zip=uxplay/

# Apple crap
# nuitka-project-if: {OS} == "Windows":
#   nuitka-project: --include-data-files={MAIN_DIRECTORY}/../apple/Bonjour64.msi=apple/
#   nuitka-project: --include-data-files={MAIN_DIRECTORY}/../apple/AppleMobileDeviceSupport64.msi=apple/

# Icon
# nuitka-project-if: {OS} == "Windows":
#   nuitka-project: --windows-icon-from-ico={MAIN_DIRECTORY}/../assets/voice_256x256.png

import os
import platform
import sys
import traceback
from multiprocessing import set_start_method
from multiprocessing.dummy import freeze_support
from types import TracebackType
from typing import Type

from loguru import logger

from app.controllers.app_controller import AppController
from app.utils import install_thirdparty
from app.utils.app_info import AppInfo
from app.views.dialogue_box import show_fatal_error

SYSTEM = platform.system()


def handle_exception(
    exc_type: Type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """
    This function is called (through excepthook) when the main application
    loop encounters an uncaught exception. When this happens, the error is
    logged to the log file and a Fatal QMessageBox is shown.
    """

    # Ignore KeyboardInterrupt exceptions, for when running through the terminal
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:  # Anything else, we want to log an error and notify the user
        logger.error(
            "The main application loop has failed with an uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        show_fatal_error(
            title="EchoView crashed",
            text="The EchoView application crashed! Sorry for the inconvenience!",
            information="Please lodge a ticket on Github to report the issue.",
            details="".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
        )

    sys.exit()


# Uncaught exceptions during the application loop are handled
# through the function above
sys.excepthook = handle_exception


def main_thread() -> None:
    app_controller = None
    try:
        app_controller = AppController()
        sys.exit(app_controller.run())
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        if app_controller:
            app_controller.quit()
    except SystemExit:
        pass
    except Exception as e:
        # Catch exceptions during initial application instantiation
        # Uncaught exceptions during the application loop are caught with excepthook
        stacktrace: str = ""
        if isinstance(e, SystemExit):
            logger.warning("Exiting application")
        else:
            stacktrace = traceback.format_exc()
        logger.error("The main application instantiation has failed with an uncaught exception:")
        logger.error(stacktrace)
        show_fatal_error(details=stacktrace)
    finally:
        logger.info("Exiting application")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "--version"]:
        try:
            from app.cli.main import cli

            cli()
        except Exception as e:
            import traceback

            print(f"Error: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
        sys.exit(0)

    debug_file_path = AppInfo().app_storage_folder / "DEBUG"
    if debug_file_path.exists() and debug_file_path.is_file() or (len(sys.argv) > 1 and sys.argv[1] == "--debug"):
        DEBUG_MODE = True
    else:
        DEBUG_MODE = False

    log_file = AppInfo().user_log_folder / (AppInfo().app_name + ".log")
    old_log_file = AppInfo().user_log_folder / (AppInfo().app_name + ".old.log")
    if old_log_file.exists() and old_log_file.is_file():
        old_log_file.unlink()
    if log_file.exists() and log_file.is_file():
        log_file.rename(old_log_file)

    format_string = "<level>[{level}]</level>[{time:YYYY-MM-DD HH:mm:ss}][{process.id}][{thread.name}][{module}][{function}][{line}] : {message}"

    # def formatter(record: "loguru.Record") -> str:
    #     """Custom formatter for loguru logger"""
    #     return "<level>[{level}]</level>[{time:YYYY-MM-DD HH:mm:ss}][{process.id}][{thread.name}][{module}][{function}][{line}] : {message}\n"

    # Remove the default stderr logger
    logger.remove()

    # Create the file logger
    logger.add(
        log_file,
        level="DEBUG" if DEBUG_MODE else "INFO",
        format=format_string,
    )

    # Add a "WARNING" or higher stderr logger
    logger.add(
        sys.stderr,
        level="DEBUG" if DEBUG_MODE else "INFO",
        format=format_string,
        colorize=True,
    )

    if "__compiled__" not in globals():
        logger.debug("Running using Python interpreter")
    else:
        # Configure QtWebEngine locales path
        os.environ["QTWEBENGINE_LOCALES_PATH"] = str(AppInfo().application_folder / "qtwebengine_locales")

        # MacOS and Windows do not support fork, and can only use spawn
        if SYSTEM != "Linux":
            logger.warning(
                "Non-Linux platform detected: using multiprocessing.freeze_support() & setting 'spawn' as MP method"
            )
            freeze_support()
            set_start_method("spawn")

        logger.debug("Running using Nuitka bundle")

    logger.info(f"Initialising EchoView application: {AppInfo().app_version}")

    # Unpack scrcpy
    if not install_thirdparty.unpack_scrcpy():
        logger.error("Failed to unpack scrcpy")
        sys.exit(1)

    if not install_thirdparty.unpack_goios():
        logger.error("Failed to unpack go-ios")
        sys.exit(1)

    if not install_thirdparty.unpack_uxplay():
        logger.error("Failed to unpack uxplay")
        sys.exit(1)

    if SYSTEM == "Windows" and not install_thirdparty.unpack_wintun():
        logger.error("Failed to unpack wintun")
        sys.exit(1)

    if SYSTEM == "Windows" and not install_thirdparty.install_bonjour():
        logger.error("Failed to install Bonjour")
        sys.exit(1)

    if SYSTEM == "Windows" and not install_thirdparty.install_AppleMobileDeviceSupport():
        logger.error("Failed to install Apple Mobile Device Support")
        sys.exit(1)

    main_thread()
