from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPaintEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QProgressBar,
    QSizePolicy,
    QWidget,
)

from app.utils.app_info import AppInfo
from app.views.devices_view import DevicesView
from app.views.overview_view import OverviewView


class TextProgressBar(QProgressBar):
    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.format())


class MainWindow(QMainWindow):
    def __init__(self, overview: OverviewView, devices: DevicesView) -> None:
        super().__init__()
        self.setWindowTitle(f"EchoView | {AppInfo().app_version}")
        self.resize(1200, 800)
        self.setMinimumSize(400, 400)
        self.setMaximumSize(1600, 1600)

        app_layout = QHBoxLayout()
        app_layout.setContentsMargins(0, 0, 0, 0)  # Space from main layout to border
        app_layout.setSpacing(0)  # Space between widgets

        self._overview = overview
        self._devices = devices

        # Set OverviewView to fixed size based on its content
        self._overview.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )

        # Add divider
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFrameShadow(QFrame.Shadow.Sunken)

        # Set DevicesView to be horizontally stretchable
        self._devices.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )

        app_layout.addWidget(self._overview)
        app_layout.addWidget(divider)
        app_layout.addWidget(self._devices)

        widget = QWidget()
        widget.setLayout(app_layout)
        self.setCentralWidget(widget)
