from typing import List

from PySide6.QtCore import QObject, Signal

from app.devices.devices import Device


class DevicesModel(QObject):
    connected_devices_updated = Signal(object)

    def __init__(self) -> None:
        super().__init__()

        self._connected_devices: List[Device] = []

    @property
    def connected_devices(self) -> List[Device]:
        return self._connected_devices

    @connected_devices.setter
    def connected_devices(self, connected_devices: List[Device]) -> None:
        if self._connected_devices != connected_devices:
            self._connected_devices = connected_devices
            self.connected_devices_updated.emit(connected_devices)
