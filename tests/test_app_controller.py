from unittest.mock import Mock

from app.controllers.app_controller import AppController


def test_connect_signals() -> None:
    controller = AppController.__new__(AppController)
    controller.overview_controller = Mock()
    controller.devices_controller = Mock()

    controller._connect_signals()

    controller.overview_controller.output_directory_changed.connect.assert_called_once_with(
        controller.devices_controller.set_output_directory
    )
    controller.overview_controller.job_number_changed.connect.assert_called_once_with(
        controller.devices_controller.set_job_number
    )
    controller.overview_controller.device_scan_requested.connect.assert_called_once_with(
        controller.devices_controller.start_scan
    )


def test_run_shows_window_scans_and_executes() -> None:
    controller = AppController.__new__(AppController)
    controller.main_window = Mock()
    controller.devices_controller = Mock()
    controller.app = Mock()
    controller.app.exec.return_value = 7

    assert controller.run() == 7
    controller.main_window.show.assert_called_once()
    controller.devices_controller.start_scan.assert_called_once()


def test_quit_and_shutdown() -> None:
    controller = AppController.__new__(AppController)
    controller.app = Mock()
    controller.devices_controller = Mock()
    controller.quit()
    controller._on_about_to_quit()
    controller.app.quit.assert_called_once()
    controller.devices_controller.shutdown.assert_called_once()


def test_theme_sets_fusion_palette() -> None:
    controller = AppController.__new__(AppController)
    controller.app = Mock()
    controller._set_theme()
    controller.app.setStyle.assert_called_once_with("Fusion")
    palette = controller.app.setPalette.call_args.args[0]
    assert palette is not None


def test_component_creation(monkeypatch) -> None:
    from app.controllers import app_controller

    controller = AppController.__new__(AppController)
    overview_model = object()
    devices_model = object()
    overview_view = object()
    devices_view = object()
    window = object()
    overview_controller = object()
    devices_controller = object()
    monkeypatch.setattr(app_controller, "OverviewModel", Mock(return_value=overview_model))
    monkeypatch.setattr(app_controller, "DevicesModel", Mock(return_value=devices_model))
    monkeypatch.setattr(app_controller, "OverviewView", Mock(return_value=overview_view))
    monkeypatch.setattr(app_controller, "DevicesView", Mock(return_value=devices_view))
    window_constructor = Mock(return_value=window)
    monkeypatch.setattr(app_controller, "MainWindow", window_constructor)
    overview_constructor = Mock(return_value=overview_controller)
    devices_constructor = Mock(return_value=devices_controller)
    monkeypatch.setattr(app_controller, "OverviewController", overview_constructor)
    monkeypatch.setattr(app_controller, "DevicesController", devices_constructor)
    controller._create_models()
    controller._create_views()
    controller._create_main_window()
    controller._create_controllers()
    assert controller.overview_model is overview_model
    assert controller.devices_model is devices_model
    window_constructor.assert_called_once_with(overview_view, devices_view)
    overview_constructor.assert_called_once_with(view=overview_view, model=overview_model)
    devices_constructor.assert_called_once_with(view=devices_view, model=devices_model)


def test_initialization_wires_application(monkeypatch) -> None:
    from app.controllers import app_controller

    application = Mock()
    monkeypatch.setattr(app_controller, "QApplication", Mock(return_value=application))
    monkeypatch.setattr(AppController, "_set_theme", Mock())
    monkeypatch.setattr(AppController, "_create_models", Mock())
    monkeypatch.setattr(AppController, "_create_views", Mock())
    monkeypatch.setattr(AppController, "_create_main_window", Mock())
    monkeypatch.setattr(AppController, "_create_controllers", Mock())
    monkeypatch.setattr(AppController, "_connect_signals", Mock())
    controller = AppController()
    assert controller.app is application
    application.setDesktopFileName.assert_called_once_with("io.github.echoview.EchoView")
    application.aboutToQuit.connect.assert_called_once_with(controller._on_about_to_quit)
