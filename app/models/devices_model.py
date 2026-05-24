from typing import List

from PySide6.QtCore import QObject, Signal

from app.devices.devices import Device


class DevicesModel(QObject):
    devices_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._devices: List[Device] = []

    @property
    def devices(self) -> List[Device]:
        return self._devices

    def set_devices(self, devices: List[Device]) -> None:
        if self._devices != devices:
            self._devices = devices
            self.devices_changed.emit()
