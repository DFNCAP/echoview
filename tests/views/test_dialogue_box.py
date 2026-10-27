from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QMessageBox, QPushButton

from app.views import dialogue_box


def test_base_dialogue_configuration_and_exec_alias(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    dialog = dialogue_box._BaseDialogue("Title", modal=False)
    qtbot.addWidget(dialog)
    assert dialog.windowTitle() == "Title"
    assert dialog.objectName() == "dialogue"
    assert not dialog.isModal()
    execute = Mock(return_value=4)
    monkeypatch.setattr(dialog, "exec", execute)
    assert dialog.exec_() == 4


def test_show_warning_populates_message_box(monkeypatch: pytest.MonkeyPatch) -> None:
    box = Mock()
    warning_icon = QMessageBox.Icon.Warning
    message_box = Mock(return_value=box)
    message_box.Icon.Warning = warning_icon
    monkeypatch.setattr(dialogue_box, "QMessageBox", message_box)
    dialogue_box.show_warning("Title", "Text", "Info", "Details")
    box.setTextFormat.assert_called_once_with(Qt.TextFormat.RichText)
    box.setIcon.assert_called_once_with(warning_icon)
    box.setWindowTitle.assert_called_once_with("Title")
    box.setText.assert_called_once_with("Text")
    box.setInformativeText.assert_called_once_with("Info")
    box.setDetailedText.assert_called_once_with("Details")
    box.exec_.assert_called_once()


def test_show_warning_uses_default_title(monkeypatch: pytest.MonkeyPatch) -> None:
    box = Mock()
    monkeypatch.setattr(dialogue_box, "QMessageBox", Mock(return_value=box))
    dialogue_box.show_warning()
    box.setWindowTitle.assert_called_once_with(dialogue_box.DEFAULT_TITLE)
    box.setText.assert_not_called()
    box.setInformativeText.assert_not_called()
    box.setDetailedText.assert_not_called()


def test_fatal_error_dialog_actions(monkeypatch: pytest.MonkeyPatch, qtbot, tmp_path: Path) -> None:
    opened = Mock()
    monkeypatch.setattr(dialogue_box.generic, "platform_specific_open", opened)
    monkeypatch.setattr(
        dialogue_box,
        "AppInfo",
        lambda: SimpleNamespace(user_log_folder=tmp_path / "logs"),
    )
    dialog = dialogue_box.FatalErrorDialog("Fatal", "Text", "Info", "Trace")
    qtbot.addWidget(dialog)
    assert dialog.details_edit.toPlainText() == "Trace"
    assert dialog.details_edit.isHidden()
    qtbot.mouseClick(dialog.details_btn, Qt.MouseButton.LeftButton)
    assert not dialog.details_edit.isHidden()
    assert dialog.details_btn.text() == "Hide Details"
    qtbot.mouseClick(dialog.details_btn, Qt.MouseButton.LeftButton)
    assert dialog.details_edit.isHidden()
    assert dialog.details_btn.text() == "Show Details"
    qtbot.mouseClick(dialog.open_log_btn, Qt.MouseButton.LeftButton)
    opened.assert_called_once_with(tmp_path / "logs")


def test_setup_error_icon_with_and_without_button(qtbot) -> None:
    dialog = QDialog()
    button = QPushButton("Details")
    qtbot.addWidget(dialog)
    layout = dialogue_box._setup_error_icon(dialog, button)
    assert layout.count() == 2
    item = layout.itemAt(1)
    assert item is not None
    assert item.widget() is button
    assert dialogue_box._setup_error_icon(dialog).count() == 1


def test_show_fatal_error_constructs_and_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    dialog = Mock()
    constructor = Mock(return_value=dialog)
    monkeypatch.setattr(dialogue_box, "FatalErrorDialog", constructor)
    dialogue_box.show_fatal_error("T", "X", "I", "D")
    constructor.assert_called_once_with("T", "X", "I", "D", parent=None)
    dialog.exec_.assert_called_once()
