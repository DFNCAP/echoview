from loguru import logger
from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from app.utils import generic
from app.utils.app_info import AppInfo


class _BaseMessageBox(QMessageBox):
    """Base message box class for all custom message boxes."""

    _dialogue_type = "base message box"

    def __init__(
        self,
        title: str,
        text: str,
        information: str,
        icon: QMessageBox.Icon,
        details: str | None = None,
        text_format: Qt.TextFormat = Qt.TextFormat.RichText,
        modal: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(modal)
        self.setObjectName("dialogue")
        self.setTextFormat(text_format)
        self.setIcon(icon)
        # Set text to be bold via rich text
        if text_format == Qt.TextFormat.RichText:
            text = f"<b>{text}</b>"
        self.setText(text)
        self.setInformativeText(information)
        if details is not None:
            self.setDetailedText(details)

        # Dynamic sizing
        self.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        )
        self.setMinimumWidth(400)

    def exec(self) -> int:
        """Executes the message box and returns the result.

        :return: The result of the message box
        :rtype: int
        """
        logger.info(
            f"Showing {self._dialogue_type} with title: [{self.windowTitle()}], text: [{self.text()}], information: [{self.informativeText()}], details: [{self.detailedText()}]"
        )
        result = super().exec()
        logger.info(
            f"Finished showing {self._dialogue_type} [{self.windowTitle()}] with result: {result}"
        )
        return result

    def exec_(self) -> int:
        """Executes the message box and returns the result.

        :return: The result of the message box
        :rtype: int
        """
        return self.exec()


class BinaryChoiceDialog(_BaseMessageBox):
    """Custom message box to display a binary choice message box."""

    def __init__(
        self,
        title: str = "",
        text: str = "",
        information: str = "",
        details: str | None = None,
        positive_text: str | None = None,
        negative_text: str | None = None,
        positive_btn: QMessageBox.StandardButton = QMessageBox.StandardButton.Yes,
        negative_btn: QMessageBox.StandardButton = QMessageBox.StandardButton.Cancel,
        default_negative: bool = True,
        icon: QMessageBox.Icon = QMessageBox.Icon.Question,
        modal: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        """Initializes the binary choice dialog.
        Used to display a binary choice message box.
        Always has two buttons, one positive and one negative.
        These buttons cannot be the same type.

        :param title: The title of the message box
        :type title: str, optional
        :param text: The main text of the message box
        :type text: str, optional
        :param information: The informative text of the message box
        :type information: str, optional
        :param details: The detailed text of the message box. If not None, a button will be displayed to show/hide this text.
        :type details: str | None, optional
        :param positive_text: The text to display on the positive button. If None, the default text of the positive button will be used.
        :type positive_text: str | None, optional
        :param negative_text: The text to display on the negative button. If None, the default text of the negative button will be used.
        :type negative_text: str | None, optional
        :param positive_btn: The type of the positive button
        :type positive_btn: QMessageBox.StandardButton, optional
        :param negative_btn: The type of the negative button
        :type negative_btn: QMessageBox.StandardButton, optional
        :param default_negative: Whether the default button is the negative button. If False, the positive button will be the default button.
        :type default_negative: bool, optional
        :param icon: The icon to display in the message box. Defaults to a question mark.
        :type icon: QMessageBox.Icon, optional
        :param parent: The parent widget
        :type parent: QWidget | None, optional
        :raises ValueError: If the positive and negative buttons are the same
        """
        super().__init__(
            title, text, information, icon, details, modal=modal, parent=parent
        )

        if positive_btn == negative_btn:
            raise ValueError("Positive and negative buttons cannot be the same")

        # Configure buttons
        self.__positive_btn = positive_btn
        self.__negative_btn = negative_btn

        self.setStandardButtons(self.positive_btn | self.negative_btn)

        if default_negative:
            self.setDefaultButton(self.negative_btn)
        else:
            self.setDefaultButton(self.positive_btn)

        # Set button text where necessary
        if positive_text is not None:
            self.button(self.positive_btn).setText(positive_text)
        if negative_text is not None:
            self.button(self.negative_btn).setText(negative_text)

    @property
    def positive_btn(self) -> QMessageBox.StandardButton:
        return self.__positive_btn

    @property
    def negative_btn(self) -> QMessageBox.StandardButton:
        return self.__negative_btn

    def exec_is_positive(self) -> bool:
        """Executes the dialog and returns whether the positive button was clicked.

        :return: True if the positive button was clicked, False otherwise.
        :rtype: bool
        """
        self.exec()
        response = self.clickedButton()
        return response == self.button(self.positive_btn)
