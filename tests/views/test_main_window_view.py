from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QSizePolicy, QWidget

from app.views import main_window_view


def test_main_window_composition(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    monkeypatch.setattr(main_window_view, "AppInfo", lambda: SimpleNamespace(app_version="1.2.3"))
    overview = QWidget()
    devices = QWidget()
    window = main_window_view.MainWindow(overview, devices)
    qtbot.addWidget(window)
    assert window.windowTitle() == "EchoView | 1.2.3"
    assert window.minimumWidth() == 1000
    assert window.minimumHeight() == 600
    assert window.centralWidget() is not None
    assert overview.sizePolicy().horizontalPolicy() is QSizePolicy.Policy.Fixed
    assert devices.sizePolicy().horizontalPolicy() is QSizePolicy.Policy.Expanding
    layout = window.centralWidget().layout()
    assert layout is not None
    assert layout.count() == 3
    overview_item = layout.itemAt(0)
    devices_item = layout.itemAt(2)
    assert overview_item is not None
    assert devices_item is not None
    assert overview_item.widget() is overview
    assert devices_item.widget() is devices


def test_text_progress_bar_renders_offscreen(qtbot) -> None:
    bar = main_window_view.TextProgressBar()
    qtbot.addWidget(bar)
    bar.setRange(0, 10)
    bar.setValue(5)
    bar.setFormat("Working %p%")
    bar.resize(200, 30)
    image = bar.grab().toImage()
    assert not image.isNull()
    assert bar.format() == "Working %p%"
