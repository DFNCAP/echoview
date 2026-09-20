import sys
from unittest.mock import Mock

import pytest


def test_main_thread_runs_controller(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import __main__ as main_module

    controller = Mock()
    controller.run.return_value = 0
    monkeypatch.setattr(main_module, "AppController", Mock(return_value=controller))
    exit_call = Mock()
    monkeypatch.setattr(main_module.sys, "exit", exit_call)

    main_module.main_thread()

    controller.run.assert_called_once()
    exit_call.assert_called_once_with(0)


def test_main_thread_reports_initialisation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import __main__ as main_module

    monkeypatch.setattr(main_module, "AppController", Mock(side_effect=RuntimeError("broken")))
    fatal = Mock()
    monkeypatch.setattr(main_module, "show_fatal_error", fatal)

    main_module.main_thread()

    fatal.assert_called_once()
    assert "broken" in fatal.call_args.kwargs["details"]


def test_handle_exception_reports_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import __main__ as main_module

    fatal = Mock()
    monkeypatch.setattr(main_module, "show_fatal_error", fatal)
    monkeypatch.setattr(main_module.sys, "exit", Mock())
    error = ValueError("bad")

    main_module.handle_exception(ValueError, error, error.__traceback__)

    fatal.assert_called_once()
    assert "ValueError: bad" in fatal.call_args.kwargs["details"]


def test_handle_exception_delegates_keyboard_interrupt(monkeypatch: pytest.MonkeyPatch) -> None:
    from app import __main__ as main_module

    original = Mock()
    monkeypatch.setattr(sys, "__excepthook__", original)
    monkeypatch.setattr(main_module.sys, "exit", Mock())
    error = KeyboardInterrupt()
    main_module.handle_exception(KeyboardInterrupt, error, error.__traceback__)
    original.assert_called_once()
