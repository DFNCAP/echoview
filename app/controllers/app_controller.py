import sys

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QApplication

from app.controllers.connected_devices_controller import ConnectedDevicesController
from app.controllers.devices_controller import DevicesController
from app.controllers.overview_controller import OverviewController
from app.models.devices_model import DevicesModel
from app.models.overview_model import OverviewModel
from app.utils.event_bus import EventBus
from app.views.devices_view import DevicesView
from app.views.main_window_view import MainWindow
from app.views.overview_view import OverviewView


class AppController(QObject):
    def __init__(self) -> None:
        super().__init__()

        self.app = QApplication(sys.argv)
        self.app.setDesktopFileName("io.github.echoview.EchoView")
        # self.app.setWindowIcon(GUIInfo().app_icon)

        self._set_theme()

        self._create_models()
        self._create_views()
        self._create_main_window()
        self._create_controllers()

    def _set_theme(self) -> None:
        self.app.setStyle("Fusion")
        pass

    def _create_models(self) -> None:
        self.overview_model = OverviewModel()
        self.devices_model = DevicesModel()
        self.event_bus = EventBus()

    def _create_views(self) -> None:
        self.overview_view = OverviewView()
        self.devices_view = DevicesView()

    def _create_main_window(self) -> None:
        self.main_window = MainWindow(self.overview_view, self.devices_view)

    def _create_controllers(self) -> None:
        self.overview_controller = OverviewController(
            view=self.overview_view,
            model=self.overview_model,
        )

        self.devices_controller = DevicesController(
            view=self.devices_view,
            model=self.devices_model,
        )

    def _connect_signals(self) -> None:
        self.overview_controller.output_directory_changed.connect(
            self.devices_controller.set_output_directory
        )
        self.overview_controller.job_number_changed.connect(
            self.devices_controller.set_job_number
        )
        self.overview_controller.device_scan_requested.connect(
            self.devices_controller.start_scan
        )

    def run(self) -> int:
        self.main_window.show()

        # Do initial device scan
        self.devices_controller.start_scan()
        # self.main_window.initialise_content(is_initial=True)
        return self.app.exec()

    def quit(self) -> None:
        self.app.quit()
