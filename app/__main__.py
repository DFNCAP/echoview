#!/usr/bin/env python3
# Compilation mode
# nuitka-project: --output-filename=EchoView
# nuitka-project: --mode=standalone
# nuitka-project: --output-dir={MAIN_DIRECTORY}/../build/

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
            details="".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)
            ),
        )

    sys.exit()


# Uncaught exceptions during the application loop are handled
# through the function above
sys.excepthook = handle_exception


# class TextProgressBar(QtWidgets.QProgressBar):
#     def paintEvent(self, event: QtGui.QPaintEvent) -> None:
#         super().paintEvent(event)
#         painter = QtGui.QPainter(self)
#         painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.format())


# class MyWidget(QtWidgets.QWidget):
#     """_summary_

#     :param QtWidgets: _description_
#     :type QtWidgets: _type_
#     """

#     def __init__(self) -> None:
#         super().__init__()

#         self.hello = ["Hallo Welt", "Hei maailma", "Hola Mundo", "Привет мир"]

#         self.button = QtWidgets.QPushButton("Click me!")
#         self.text = QtWidgets.QLabel(
#             "Hello World", alignment=Qt.AlignmentFlag.AlignCenter
#         )
#         self.version = QtWidgets.QLabel(
#             AppInfo().app_name, alignment=Qt.AlignmentFlag.AlignCenter
#         )

#         self.prog = TextProgressBar(
#             minimum=0, maximum=0, format="Hello", textVisible=True
#         )

#         self._layout = QtWidgets.QVBoxLayout(self)
#         self._layout.addWidget(self.text)
#         self._layout.addWidget(self.button)
#         self._layout.addWidget(self.version)
#         self._layout.addWidget(self.prog)

#         self.button.clicked.connect(self.magic)

#     @Slot()
#     def magic(self) -> None:
#         self.text.setText(random.choice(self.hello))


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
        logger.warning("Exiting application")
    except Exception as e:
        # Catch exceptions during initial application instantiation
        # Uncaught exceptions during the application loop are caught with excepthook
        stacktrace: str = ""
        if isinstance(e, SystemExit):
            logger.warning("Exiting application")
        else:
            stacktrace = traceback.format_exc()
        logger.error(
            "The main application instantiation has failed with an uncaught exception:"
        )
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
    if (
        debug_file_path.exists()
        and debug_file_path.is_file()
        or (len(sys.argv) > 1 and sys.argv[1] == "--debug")
    ):
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
        os.environ["QTWEBENGINE_LOCALES_PATH"] = str(
            AppInfo().application_folder / "qtwebengine_locales"
        )

        # MacOS and Windows do not support fork, and can only use spawn
        if SYSTEM != "Linux":
            logger.warning(
                "Non-Linux platform detected: using multiprocessing.freeze_support() & setting 'spawn' as MP method"
            )
            freeze_support()
            set_start_method("spawn")

        logger.debug("Running using Nuitka bundle")

    logger.info(f"Initialising EchoView application: {AppInfo().app_version}")

    main_thread()

    # app = QtWidgets.QApplication([])

    # widget = MyWidget()
    # widget.resize(800, 600)
    # widget.show()

    # sys.exit(app.exec())
