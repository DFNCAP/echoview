from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt

from app.views import overview_view


@pytest.fixture
def view(monkeypatch: pytest.MonkeyPatch, qtbot, tmp_path: Path):
    monkeypatch.setattr(overview_view, "AppInfo", lambda: SimpleNamespace(user_log_folder=tmp_path / "logs"))
    widget = overview_view.OverviewView()
    qtbot.addWidget(widget)
    return widget


def test_text_fields_emit_values(view, qtbot, tmp_path: Path) -> None:
    view._dir_entry.setText(str(tmp_path))
    with qtbot.waitSignal(view.output_directory_changed) as directory_signal:
        view._on_output_directory_changed()
    view._job_number.setText("JOB-1")
    with qtbot.waitSignal(view.job_number_changed) as job_signal:
        view._on_job_number_changed()
    assert directory_signal.args == [tmp_path.resolve()]
    assert job_signal.args == ["JOB-1"]


def test_directory_picker(view, qtbot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(overview_view.QFileDialog, "getExistingDirectory", lambda *args, **kwargs: str(tmp_path))
    with qtbot.waitSignal(view.output_directory_changed):
        view._pick_directory()
    assert view._dir_entry.text() == str(tmp_path.resolve())


def test_refresh_emits_scan(view, qtbot) -> None:
    with qtbot.waitSignal(view.device_scan_requested):
        qtbot.mouseClick(view._device_scan_btn, Qt.MouseButton.LeftButton)


def test_open_log_button(view, qtbot, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    open_path = Mock()
    monkeypatch.setattr(overview_view, "platform_specific_open", open_path)
    qtbot.mouseClick(view._open_log_directory, Qt.MouseButton.LeftButton)
    open_path.assert_called_once_with(tmp_path / "logs")
