from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

LOGO = """
 _____     _           _   _ _               
|  ___|   | |         | | | (_)              
| |__  ___| |__   ___ | | | |_  _____      __
|  __|/ __| '_ \ / _ \| | | | |/ _ \ \ /\ / /
| |__| (__| | | | (_) \ \_/ / |  __/\ V  V / 
\____/\___|_| |_|\___/ \___/|_|\___| \_/\_/                                            
"""


class OverviewView(QWidget):
    output_directory_changed = Signal(Path)
    job_number_changed = Signal(str)
    device_scan_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        logger.debug("Initializing OverviewView")

        self._layout = QVBoxLayout()
        self._logo = self._create_logo()
        self._layout.addWidget(self._logo)

        self._file_selector = self._create_file_selector()
        self._layout.addWidget(self._file_selector)

        self._job_number = self._create_job_number_field()
        self._layout.addWidget(self._job_number)

        self._device_scan_btn = self._create_device_scan_btn()
        self._layout.addWidget(self._device_scan_btn)

        self.setLayout(self._layout)

        # Constrain width to logo size + layout padding so logo isn't cut off
        margins = self._layout.contentsMargins()
        self.setMaximumWidth(
            self._logo.sizeHint().width() + margins.left() + margins.right()
        )

    def _create_logo(self) -> QWidget:
        logo = QLabel(LOGO)
        logo.setTextFormat(Qt.TextFormat.PlainText)
        logo.setAlignment(Qt.AlignmentFlag.AlignTop)

        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        logo.setFont(font)

        return logo

    def _create_file_selector(self) -> QWidget:
        layout = QHBoxLayout()
        self._dir_entry = QLineEdit(placeholderText="output directory")
        self._dir_entry.editingFinished.connect(self._on_output_directory_changed)

        layout.addWidget(self._dir_entry)

        btn = QPushButton()
        btn.setToolTip("Select Directory")
        btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        btn.setFixedSize(28, 28)
        btn.clicked.connect(self._pick_directory)
        layout.addWidget(btn)

        widget = QWidget()
        widget.setLayout(layout)

        return widget

    def _pick_directory(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            "",
            QFileDialog.Option.ShowDirsOnly | QFileDialog.Option.DontResolveSymlinks,
        )

        if path:
            resolved = Path(path).resolve()
            self._dir_entry.setText(str(resolved))
            self._on_output_directory_changed()

    def _on_output_directory_changed(self) -> None:
        self.output_directory_changed.emit(Path(self._dir_entry.text()).resolve())

    def _create_job_number_field(self) -> QLineEdit:
        job_number = QLineEdit(placeholderText="job number")
        job_number.editingFinished.connect(self._on_job_number_changed)
        return job_number

    def _on_job_number_changed(self) -> None:
        self.job_number_changed.emit(self._job_number.text())

    def _create_device_scan_btn(self) -> QPushButton:
        btn = QPushButton("Scan for Devices")
        btn.clicked.connect(self._on_device_scan_pressed)
        return btn

    def _on_device_scan_pressed(self) -> None:
        logger.info("Requesting device scan from view")
        self.device_scan_requested.emit()

    # def set_directory_label(self, directory: str) -> None:
    #     self._dir_entry.setText(directory)
    #     self.output_directory_changed.emit(directory)

    # def set_job_number(self, job_number: str) -> None:
    #     self._job_number.setText(job_number)
    #     self.job_number_changed.emit(job_number)
