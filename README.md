# EchoView

**EchoView** is a cross-platform (Windows + Linux) desktop GUI, built on PySide6 / Qt6, that
connects to Android and iOS devices over USB and extracts data from them. It is a
single-user, point-and-click tool — not a web service or a daemon.

## Features

- **Device scan** — automatically detect connected Android and iOS devices (a USB
  plug/unplug event re-triggers a scan).
- **Screenshot** — capture the current screen of either platform.
- **Screen recording** — record the device screen (Android via `scrcpy`, iOS via `UxPlay` /
  AirPlay).
- **Autoscroll & autoscroll-screenshot** — scroll a screen automatically, and capture a
  screenshot on each step, stopping when the screen stops changing.
- **Backup** — dump installed/system packages and `/sdcard` folders (Android).
- **Contact extraction** — export the device's contacts (Android).
- **Device-info & log extraction** — dump properties, settings, app lists (Android), or
  installed apps and device info (iOS), plus logcat / bug reports (Android).
- **Status & progress** — long-running operations report their status and progress in the
  GUI and can be cancelled.

Contact extraction and full backups are currently **Android-only**; on iOS the equivalent
methods are not implemented.

## Usage

The pre-built binary is self-contained: the third-party tooling (go-ios, scrcpy + adb,
UxPlay, and on Windows wintun + the Apple support) is fetched and unpacked automatically on
first launch, so no setup is required. Simply launch `EchoView` and work entirely from the
GUI:

1. Connect a device (Android with USB debugging on, and/or iOS over USB). EchoView watches
   for USB plug/unplug and re-scans automatically; you can also trigger a scan manually.
2. Select a device in the device list and use its action buttons:

   | Action                             | Android |   iOS    |
   | ---------------------------------- | :-----: | :------: |
   | Screenshot                         |    ✓    |    ✓     |
   | Screen recording                   |    ✓    |    ✓     |
   | Autoscroll / autoscroll-screenshot |    ✓    |    ✓     |
   | Backup                             |    ✓    |    —     |
   | Extract contacts                   |    ✓    |    —     |
   | Extract device info / logs         |    ✓    | ✓ (info) |

   Long-running operations show a status line and a progress bar, and can be cancelled.

3. **Enable iOS developer mode.** iOS devices only appear with full access once developer
   mode is enabled. From the device panel, choose _Enable Developer Mode_ (this **reboots the
   device**). On iOS 16 or later it must be toggled on the device itself; if a **passcode is
   set**, developer mode cannot be enabled programmatically — enable it on the device manually
   and rescan. On iOS 15 and earlier the app can also mount the development image for you.

> **Developing from source?** See [`DEVELOPMENT.md`](DEVELOPMENT.md) for prerequisites,
> building, running in dev mode, and the test/lint tooling.

## Troubleshooting

**No Android device found.** Confirm USB debugging is enabled on the device and that it is
connected and authorized. EchoView uses the bundled `adb` (from `scrcpy/`).

**No iOS device found / no full access.**

- On Linux, `usbmuxd` must be installed _and_ active:

  ```bash
  sudo systemctl status usbmuxd
  ```

- For full access the device needs **developer mode** enabled (see
  [Enable iOS developer mode](#usage)). If a passcode is set, enable developer mode on the
  device itself, then rescan.
- EchoView starts a `go-ios` tunnel automatically when `usbmuxd` is up; if iOS detection
  still fails, restart the app so the tunnel can be re-established.

**iOS AirPlay / UxPlay connection fails (Windows).** UxPlay listens for inbound AirPlay
traffic, so a firewall may block it. See [Firewall rules (Windows)](#firewall-rules-windows).
For deeper UxPlay diagnosis (mDNS/Avahi, GStreamer plugins, ports), see the
[UxPlay troubleshooting guide](submodules/UxPlay/README.md#troubleshooting).

**Logs.** To get a verbose log, launch with `--debug`, or drop an empty `DEBUG` file into
EchoView's app storage folder. Logs are written to the user log folder (`EchoView.log`, with
the previous run rotated to `EchoView.old.log`).

## Firewall rules (Windows)

iOS AirPlay mirroring (UxPlay) needs an inbound firewall rule. If inbound connections are
disabled, create one for `uxplay.exe`:

1. Open `secpol.msc` (Start > `secpol.msc`).
2. Navigate to _Windows Defender Firewall with Advanced Security > Inbound Rules_.
3. Right-click > _New Rule..._.
4. Select **Program** and hit _Next_.
5. Select _This program path:_, and the full path to `uxplay.exe` within the EchoView
   installation directory (e.g. `C:\Users\USER\echoview\uxplay\bin\uxplay.exe`), then
   _Next_.
6. Select _Allow the connection_ and hit _Next_.
7. Allow the **Private** and **Public** profiles, then _Next_.
8. Name it something like `uxplay` and hit _Finish_.
9. Restart EchoView and try to connect again.

## License

EchoView bundles:

- **[go-ios](https://github.com/danielpaulus/go-ios)** (MIT) — iOS tooling.
- **[scrcpy](https://github.com/Genymobile/scrcpy)** and **adb** (Apache 2.0) — Android
  tooling.
- **[UxPlay](https://github.com/FDH2/UxPlay)** — iOS AirPlay mirroring (a git submodule).
- On Windows: **Bonjour** / **AppleMobileDeviceSupport** (see
  [`apple/README.md`](apple/README.md)).
