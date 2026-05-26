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

DEFAULT_TITLE = "EchoView"


class _BaseDialogue(QDialog):
    """Base dialogue class for all custom dialogues."""

    _dialogue_type = "base dialogue box"

    def __init__(
        self,
        title: str,
        modal: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)

        # Set up the message box
        self.setWindowTitle(title)
        self.setModal(modal)
        self.setObjectName("dialogue")

        # Dynamic sizing
        self.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        )

    def exec(self) -> int:
        """Executes the message box and returns the result.

        :return: The result of the message box
        :rtype: int
        """
        logger.info(f"Showing {self._dialogue_type} with title: {self.windowTitle()}")
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


def show_warning(
    title: str | None = None,
    text: str | None = None,
    information: str | None = None,
    details: str | None = None,
    parent: QWidget | None = None,
) -> None:
    """Creates a warning dialogue. Utilizes the warning icon.

    :param title: Window title
    :type title: str | None
    :param text: Short text description
    :type text: str | None
    :param information: Long form information
    :type information: str | None
    :param details: Optional details that are hidden in a sub menu
    :type details: str | None
    :param parent: The parent widget
    :type parent: QWidget | None
    """
    # jscpd:ignore-end
    logger.info(
        f"Showing warning box with input: [{title}], [{text}], [{information}], [{details}]"
    )

    # Set up the message box
    warning_message_box = QMessageBox(parent=parent)
    warning_message_box.setTextFormat(Qt.TextFormat.RichText)
    warning_message_box.setIcon(QMessageBox.Icon.Warning)
    warning_message_box.setObjectName("dialogue")
    if title:
        warning_message_box.setWindowTitle(title)
    else:
        warning_message_box.setWindowTitle(DEFAULT_TITLE)

    # Add data
    if text:
        warning_message_box.setText(text)
    if information:
        warning_message_box.setInformativeText(information)
    if details:
        warning_message_box.setDetailedText(details)

    # Show the message box
    logger.debug("Finished showing warning box")
    warning_message_box.exec_()


class FatalErrorDialog(_BaseDialogue):
    """Custom dialog to display fatal errors.

    Has button to show more details, open the log directory, and upload the log file to 0x0.
    """

    def __init__(
        self,
        title: str = "Fatal Error",
        text: str = "A fatal error has occurred!",
        information: str = "Please report the error to the developers.",
        details: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(title, parent=parent)

        # Add data
        self.text = text
        self.information = information
        self.details = details

        # Buttons
        self.details_btn = QPushButton("Show Details")
        self.close_btn = QPushButton("Close")
        self.open_log_btn = QPushButton("Open Log Directory")

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.open_log_btn)
        btn_layout.addWidget(self.close_btn)

        # Details
        self.details_edit = QPlainTextEdit()
        self.details_edit.setPlainText(self.details)
        self.details_edit.setMaximumHeight(150)
        self.details_edit.setReadOnly(True)
        self.details_edit.setHidden(True)

        # Set up the layout
        layout = QVBoxLayout()
        main_layout = QHBoxLayout()
        main_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # Left-side
        l_layout = _setup_error_icon(self, self.details_btn)
        main_layout.addLayout(l_layout)

        # Center spacer
        main_layout.addItem(QSpacerItem(20, 20))

        # Right-side
        r_layout = QVBoxLayout()

        txt = QLabel(self.text)
        txt.setWordWrap(True)
        r_layout.addWidget(QLabel(self.text))

        info = QLabel(self.information)
        info.setWordWrap(True)
        r_layout.addWidget(info)

        r_layout.addLayout(btn_layout)
        main_layout.addLayout(r_layout)

        layout.addLayout(main_layout)
        layout.addWidget(self.details_edit)

        self.setLayout(layout)
        self.setFixedWidth(self.sizeHint().width())

        # Connect buttons
        def _toggle_details() -> None:
            self.details_edit.setHidden(not self.details_edit.isHidden())
            if self.details_edit.isHidden():
                self.details_btn.setText("Show Details")
            else:
                self.details_btn.setText("Hide Details")
            self.adjustSize()

        self.close_btn.clicked.connect(self.close)
        self.open_log_btn.clicked.connect(
            lambda: generic.platform_specific_open(AppInfo().user_log_folder)
        )

        self.details_btn.clicked.connect(lambda: _toggle_details())


def _setup_error_icon(
    diag: QDialog, details_btn: QPushButton | None = None
) -> QVBoxLayout:
    l_layout = QVBoxLayout()
    piximap = getattr(QStyle, "SP_MessageBoxCritical")
    icon = diag.style().standardIcon(piximap)
    label = QLabel()
    label.setPixmap(icon.pixmap(64, 64))
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    l_layout.addWidget(label)
    if details_btn is not None:
        l_layout.addWidget(details_btn)
    l_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return l_layout


def show_fatal_error(
    title: str = "Fatal Error",
    text: str = "A fatal error has occurred!",
    information: str = "Please report the error to the developers.",
    details: str = "",
    parent: QWidget | None = None,
) -> None:
    """
    Displays a critical error message box, containing text,
    information, and details. Currently only called if there
    are any hard exceptions that cause the main app exec
    loop to stop functioning.

    :param title: text to pass to setWindowTitle
    :param text: text to pass to setText
    :param information: text to pass to setInformativeText
    :param details: text to pass to setDetailedText
    :param parent: The parent widget
    """
    logger.info(
        f"Showing fatal error box with input: [{title}], [{text}], [{information}], [{details}]"
    )

    diag = FatalErrorDialog(title, text, information, details, parent=parent)
    diag.exec_()
