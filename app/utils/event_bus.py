from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    """Central event bus for cross-component communication."""

    # Device operation events
    operation_started = Signal(str, str)  # device_id, operation_type
    operation_finished = Signal(str, str, object)  # device_id, operation_type, result
    operation_error = Signal(str, str, str)  # device_id, operation_type, error

    # Device request events
    screenshot_requested = Signal(object)  # Device
    backup_requested = Signal(object)  # Device
