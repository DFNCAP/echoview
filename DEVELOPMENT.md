# EchoView — Development

This guide is for contributors and anyone who wants to run EchoView from source or build the
distribution. End users of the pre-built binary only need
[`README.md`](README.md).

## Prerequisites

### All platforms

- **Python** exactly `3.12.*` (pinned in `pyproject.toml` and `.python-version`).
- **[`uv`](https://github.com/astral-sh/uv)** — install it and make sure `uv` is on your
  command line.
- A supported **Android** device with **USB debugging** enabled, and/or a supported
  **iOS** device connected by USB.

### Windows

To work with **iOS** devices on Windows, you must supply the Apple components yourself —
it is against Apple's EULA to distribute them, so they are not bundled. See
[`apple/README.md`](apple/README.md) for how to obtain `Bonjour64.msi`,
`BonjourSDK64.msi`, and `AppleMobileDeviceSupport64.msi`.

If your firewall blocks inbound connections, an iOS AirPlay (UxPlay) connection will fail
until you allow it — see [Firewall rules (Windows)](README.md#firewall-rules-windows).

### Linux

Install the gstreamer plugins and `usbmuxd` before running:

```bash
sudo apt install gstreamer1.0-plugins-base gstreamer1.0-libav gstreamer1.0-plugins-good gstreamer1.0-plugins-bad usbmuxd
```

`usbmuxd` must be running for iOS devices to be detected.

## Getting started

1. Clone the repository **with its submodules** (UxPlay is a submodule):

   ```bash
   git clone --recurse-submodules https://github.com/DFNCAP/echoview.git
   ```

2. Install the dependencies into the virtual environment. The runtime and dev tooling live in
   separate groups, so sync both:

   ```bash
   uv sync --group dev
   ```

3. **Run in development:**

   ```bash
   uv run -m app
   ```

   The first launch fetches and unpacks the bundled third-party tools (go-ios, scrcpy + adb,
   UxPlay, and on Windows wintun + the Apple support), so it is slower than usual.
   `uv run build.py run` is equivalent to `uv run -m app`.

### Building a standalone distribution

To produce a distributable build (this also fetches the runtime tools and runs Nuitka):

```bash
uv run build.py
```

- On **Windows** the result is an archive under `build/EchoView-<version>-win64.zip`.
- On **Linux** the result is `build/EchoView-<version>-linux.tar.gz`.

Clean build artifacts with `uv run build.py clean` (add `clean_all` to also remove `.venv`).

## CLI

EchoView is primarily a GUI, but the entry point exposes two flags:

```bash
uv run -m app --help      # print help
uv run -m app --version   # print the version
```

## Debugging

To get a verbose log, launch with `--debug`, or drop an empty `DEBUG` file into EchoView's
app storage folder. Logs are written to the user log folder (`EchoView.log`, with the
previous run rotated to `EchoView.old.log`).

## Common commands

| Task                                                       | Command                                                         |
| ---------------------------------------------------------- | --------------------------------------------------------------- |
| Build (fetches runtime deps, runs Nuitka, archives output) | `uv run build.py`                                               |
| Run in dev mode                                            | `uv run -m app` (or `uv run build.py run`)                      |
| Clean build artifacts                                      | `uv run build.py clean` (`clean_all` also removes `.venv`)      |
| Run tests                                                  | `uv run pytest`                                                 |
| Run one test / case                                        | `uv run pytest tests/devices/test_android.py` / `... -k <name>` |
| Lint                                                       | `uv run ruff check .`                                           |
| Format                                                       | `uv run ruff format .`                                          |
| Type check                                                 | `uv run basedpyright`                                           |

Note: `uv run -m app` only works after `build.py` (or a launch) has run at least once,
because that is when the bundled third-party tooling is fetched and unpacked. The test suite
and lint/type checks exclude `submodules/`.
