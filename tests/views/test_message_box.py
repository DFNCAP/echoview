from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from app.views.message_box import BinaryChoiceDialog, _BaseMessageBox


def test_base_message_box_configuration(qtbot) -> None:
    dialog = _BaseMessageBox(
        "Title",
        "Text",
        "Information",
        QMessageBox.Icon.Warning,
        details="Details",
    )
    qtbot.addWidget(dialog)
    assert dialog.windowTitle() == "Title"
    assert dialog.text() == "<b>Text</b>"
    assert dialog.informativeText() == "Information"
    assert dialog.detailedText() == "Details"
    assert dialog.isModal()
    assert dialog.minimumWidth() == 400


def test_base_message_box_plain_text_without_details(qtbot) -> None:
    dialog = _BaseMessageBox(
        "Title",
        "Text",
        "Information",
        QMessageBox.Icon.Information,
        text_format=Qt.TextFormat.PlainText,
        modal=False,
    )
    qtbot.addWidget(dialog)
    assert dialog.text() == "Text"
    assert dialog.detailedText() == ""
    assert not dialog.isModal()


def test_exec_alias_delegates(monkeypatch: pytest.MonkeyPatch, qtbot) -> None:
    dialog = _BaseMessageBox("T", "X", "I", QMessageBox.Icon.NoIcon)
    qtbot.addWidget(dialog)
    execute = Mock(return_value=7)
    monkeypatch.setattr(dialog, "exec", execute)
    assert dialog.exec_() == 7
    execute.assert_called_once()


def test_binary_choice_configuration(qtbot) -> None:
    dialog = BinaryChoiceDialog(
        title="Choose",
        text="Proceed?",
        information="Info",
        positive_text="Continue",
        negative_text="Stop",
        default_negative=False,
    )
    qtbot.addWidget(dialog)
    assert dialog.positive_btn is QMessageBox.StandardButton.Yes
    assert dialog.negative_btn is QMessageBox.StandardButton.Cancel
    assert dialog.button(dialog.positive_btn).text() == "Continue"
    assert dialog.button(dialog.negative_btn).text() == "Stop"
    assert dialog.defaultButton() is dialog.button(dialog.positive_btn)


def test_binary_choice_defaults_to_negative(qtbot) -> None:
    dialog = BinaryChoiceDialog()
    qtbot.addWidget(dialog)
    assert dialog.defaultButton() is dialog.button(dialog.negative_btn)


def test_binary_choice_rejects_identical_buttons(qtbot) -> None:
    with pytest.raises(ValueError, match="cannot be the same"):
        BinaryChoiceDialog(
            positive_btn=QMessageBox.StandardButton.Yes,
            negative_btn=QMessageBox.StandardButton.Yes,
        )


@pytest.mark.parametrize("positive", [True, False])
def test_exec_is_positive(monkeypatch: pytest.MonkeyPatch, qtbot, positive: bool) -> None:
    dialog = BinaryChoiceDialog()
    qtbot.addWidget(dialog)
    monkeypatch.setattr(dialog, "exec", Mock(return_value=0))
    selected = dialog.button(dialog.positive_btn if positive else dialog.negative_btn)
    monkeypatch.setattr(dialog, "clickedButton", Mock(return_value=selected))
    assert dialog.exec_is_positive() is positive
