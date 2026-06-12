# README
## Getting Started
1. `git clone --recurse-submodules https://github.com/DFNCAP/echoview.git`
2. WINDOWS ONLY: Please read the README.me in `apple/README.md` to ensure you have the necessary Apple device drivers
3. Ensure `uv` is installed and available on the commandline.
4. `uv run build.py` -> This will fetch and install all necessary runtime dependencies.
5. `uv run -m app` -> This will run EchoView in a development environment. Note that `build.py` must have been run once to fetch the necessary runtime dependencies.

## Firewall Rules - Windows Only
If inbound connections are disabled, a new inbound rule should be created:
1. Start > secpol.msc
2. Navigate to Windows Defender Firewall with Advanced Security > Windows Defender Firewall with Advanced Security - Local Group Policy Object > Inbound Rules
3. Right click > New Rule...
4. Select `Program` and hit Next
5. Select `This program path:`, and the full file path to `uxplay.exe` within the EchoView installation directory (e.g. `C:\Users\USER\echoview\uxplay\bin\uxplay.exe`), hit Next
6. Select `Allow the connection` and hit Next
7. Allow profiles `Private` and `Public`, hit Next
8. Name it something like `uxplay` and hit Finish.
9. Restart the server and try to connect again.

# Running on Linux
```bash
sudo apt install sudo apt install gstreamer1.0-plugins-base gstreamer1.0-libav gstreamer1.0-plugins-good gstreamer1.0-plugins-bad
```

## License
This project bundles go-ios (MIT) and scrcpy (Apache 2.0).
