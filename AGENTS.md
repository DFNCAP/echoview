# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository.

## What this is

**EchoView** is a cross-platform (Windows + Linux) PySide6 / Qt6 desktop GUI that
scans connected Android and iOS devices and extracts data from them: device scan,
screenshots, screen recording, autoscroll capture, backups, contact extraction, and
device info/log extraction. It is a single-user tool, not a web service.

## Environment

- **Python**: exactly `3.12.*` (pinned in `pyproject.toml` and `.python-version`).
- **Package manager**: `uv`. Run *everything* through `uv run ...` so the venv is
  activated. Install dev tooling with `uv sync --group dev`.
- **Platforms**: Windows and Linux are the supported runtime targets. Code branches on
  `platform.system()` / `sys.platform`; there is no documented macOS runtime path even
  though some Nuitka directives mention Darwin.

## Common commands

| Task | Command |
| --- | --- |
| Build (fetches runtime deps, runs Nuitka, archives output) | `uv run build.py` |
| Run in dev mode | `uv run -m app` |
| Run via build script | `uv run build.py run` |
| Clean build artifacts | `uv run build.py clean` (adds `.venv` with `clean_all`) |
| Run tests | `uv run pytest` |
| Run one test file / case | `uv run pytest tests/devices/test_android.py` / `... -k <name>` |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format .` |
| Type check | `uv run basedpyright` |

Note: `uv run -m app` only works after `build.py` has run at least once, because it
fetches/unpacks the third-party tooling.

## Project layout

```
app/                 Application package (the only pip-installable package)
  __main__.py        Entry point: sets up logging, unpacks tools, starts AppController
  controllers/       QObject-based controllers; wire views<->models, run background jobs
  models/            Data models (devices, overview)
  views/             PySide6 widgets (main window, device widget, dialogs)
  devices/           Device abstraction: Device ABC + AndroidDevice/iOSDevice + per-OS modules
  utils/             app_info (singleton), generic helpers, subprocess helpers, third-party install
  cli/               click CLI used for --help / --version
tests/               pytest suite, mirrors the app/ package layout
build.py             Nuitka build driver (also exposes run/clean/clean_all subcommands)
submodules/UxPlay/   Git submodule (iOS AirPlay); excluded from lint/test discovery
```

### Architecture notes

- **MVC.** `AppController` (`app/controllers/app_controller.py`) creates the models and
  views, instantiates the per-feature controllers, and connects Qt signals between them.
- **Device abstraction.** `Device` is an abstract dataclass in
  `app/devices/devices.py`; `AndroidDevice` and `iOSDevice` subclass it. Platform
  behaviour lives in module-level functions in `android.py` / `ios.py` (e.g.
  `get_connected_devices`, `screenshot`), not only on the class.
- **Status reporting.** Long operations take a `reporter: StatusReporter` (or a
  `NullReporter()` default) that emits `status_changed` / `progress_changed` signals.
- **Cancellation.** Background operations accept a `cancelled: threading.Event` and must
  check `cancelled.is_set()` in their loops.
- **Threading.** `DeviceOperationRunner` (`devices_controller.py`) runs operations on a
  `ThreadPoolExecutor` and emits `operation_started` / `operation_finished` /
  `operation_error` Qt signals; the controller connects these and marshals results back to
  the GUI thread. USB plug/unplug comes from `USBMonitor` and is coalesced with a
  single-shot `QTimer` before triggering a scan.
- **Logging.** Use `loguru`'s `logger` (configured in `app/__main__.py`), not stdlib
  `logging`. `--debug`, or a `DEBUG` file in the app storage folder, enables DEBUG level.

## Coding conventions

- **Type hints** on all public functions and signatures; use `X | None` unions and
  `pathlib.Path` (not string paths) for file locations.
- **Docstrings** in Sphinx style (see `.vscode/settings.json` `autoDocstring.docstringFormat`).
- **Formatting** (from `pyproject.toml`): 4-space indent, 120-char lines, double quotes,
  isort import sorting. Ruff is the formatter and linter; `F401` is intentionally not
  auto-fixed. Run `ruff format` before committing.
- **Subprocesses**: go through `app.utils.subprocess_helpers.run` / `popen` so Windows
  suppresses the console window (`CREATE_NO_WINDOW`). Don't call raw `subprocess`.
- **External executables** are resolved via `AppInfo` properties (`adb_path`,
  `scrcpy_path`, `goios_path`, `uxplay_path`) and wrapped in module-level helpers
  (`_adb()`, `_scrcpy()`, `_goios()`, `_uxplay()`) so tests can monkeypatch them.

## Testing

- Framework: `pytest` with `pytest-qt` and `pytest-cov`. Tests live in `tests/` and
  mirror `app/`. Config in `pyproject.toml`: `--import-mode=importlib`,
  `--strict-markers`, `pythonpath="."`, coverage `fail_under = 80` (branch coverage on).
- Qt tests run headless: `conftest.py` sets `QT_QPA_PLATFORM=offscreen`.
- The suite excludes `submodules/`.
- Reuse the shared fixtures in `tests/conftest.py`: `fake_reporter`, `completed_process`,
  `android_device`, `ios_device`, `app_info_stub`. `AppInfo` is a singleton — the
  autouse `reset_app_info` fixture clears `AppInfo._instance`, and `app_info_stub`
  redirects its folders to `tmp_path`.
- Prefer `monkeypatch` on module-level helpers (`android._adb`, `android.run`,
  `android.popen`, etc.) and `tmp_path` for file outputs over real I/O. Mark
  multi-component tests with `@pytest.mark.integration`.

## Bundled third-party tools

`build.py` fetches and, at startup, `app/utils/install_thirdparty.py` unpacks:
**go-ios** (iOS, MIT), **scrcpy + adb** (Android, Apache-2.0), **UxPlay** (iOS AirPlay),
and on Windows **wintun** + **Bonjour / AppleMobileDeviceSupport**. Linux additionally
needs `usbmuxd` and the gstreamer plugins (see `README.md`). Windows Apple support
requires manually extracting MSIs into `apple/` — see `apple/README.md`.

## Gotchas / do-not-touch

- **Do not edit `app/_version.py`** — it is auto-generated by `build.py` via dunamai and
  git-ignored.
- **Do not modify `submodules/UxPlay`** — it's a git submodule and excluded from lint/tests.
- iOS developer mode cannot be enabled while a passcode is set; `enable_devmode` raises
  `PasscodeEnabledError` in that case.
- On non-Linux platforms the app forces `spawn` + `multiprocessing.freeze_support()`.
- Generated artifacts (`build/`, `dist/`, `*.build/`, logs, `selfIdentity.plist`,
  `version.xml`) are git-ignored — don't commit them.

## Commit messages

Imperative mood, capitalized, ≤50-char subject, no trailing punctuation; use a short
body only when it adds information (see the user's global commit convention).
