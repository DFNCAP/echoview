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
    QSizePolicy,
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

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self._logo = self._create_logo()
        layout.addWidget(self._logo)

        self._file_selector = self._create_file_selector()
        layout.addWidget(self._file_selector)

        self._job_number = self._create_job_number_field()
        layout.addWidget(self._job_number)

        layout.addStretch()

        self._device_scan_btn = self._create_device_scan_btn()
        layout.addWidget(self._device_scan_btn)

        self.setLayout(layout)

    def _create_logo(self) -> QWidget:
        logo = QLabel(LOGO)
        logo.setTextFormat(Qt.TextFormat.PlainText)
        logo.setAlignment(Qt.AlignmentFlag.AlignTop)

        font = QFont("monospace")
        font.setStyleHint(QFont.StyleHint.TypeWriter)
        logo.setFont(font)
        logo.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Maximum)

        # logo.setStyleSheet("background: red")

        return logo

    def _create_file_selector(self) -> QWidget:
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        self._dir_entry = QLineEdit(placeholderText="Output Directory")
        self._dir_entry.editingFinished.connect(self._on_output_directory_changed)

        layout.addWidget(self._dir_entry)

        btn = QPushButton()
        btn.setToolTip("Select Directory")
        btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))
        btn.setFixedSize(25, 25)
        btn.clicked.connect(self._pick_directory)
        layout.addWidget(btn)

        widget = QWidget()
        widget.setLayout(layout)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # widget.setStyleSheet("background: green")

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
        job_number = QLineEdit(placeholderText="Job Number")
        job_number.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        job_number.editingFinished.connect(self._on_job_number_changed)

        # job_number.setStyleSheet("background: blue")

        return job_number

    def _on_job_number_changed(self) -> None:
        self.job_number_changed.emit(self._job_number.text())

    def _create_device_scan_btn(self) -> QPushButton:
        btn = QPushButton("Scan for Devices")
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        btn.clicked.connect(self._on_device_scan_pressed)

        # btn.setStyleSheet("background: red")

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
