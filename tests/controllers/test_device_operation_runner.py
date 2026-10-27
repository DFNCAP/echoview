from app.controllers.devices_controller import DeviceOperationRunner
from app.devices.devices import OperationType


def test_run_emits_success_signals(qtbot) -> None:
    runner = DeviceOperationRunner()
    started = []
    finished = []
    runner.operation_started.connect(lambda *args: started.append(args))
    runner.operation_finished.connect(lambda *args: finished.append(args))

    runner._run("device", OperationType.SCREENSHOT, lambda: "result")

    assert started == [("device", OperationType.SCREENSHOT)]
    assert finished == [("device", OperationType.SCREENSHOT, "result")]
    runner.shutdown()


def test_run_emits_error_signal() -> None:
    runner = DeviceOperationRunner()
    errors = []
    runner.operation_error.connect(lambda *args: errors.append(args))

    def fail() -> None:
        raise ValueError("broken")

    runner._run("device", OperationType.BACKUP, fail)

    assert errors == [("device", OperationType.BACKUP, "broken")]
    runner.shutdown()


def test_submit_uses_executor(qtbot) -> None:
    runner = DeviceOperationRunner()
    with qtbot.waitSignal(runner.operation_finished, timeout=2000) as signal:
        runner.submit("device", OperationType.SCREENSHOT, lambda: 42)
    assert signal.args == ["device", OperationType.SCREENSHOT, 42]
    runner.shutdown()
