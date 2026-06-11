# README
## Getting Started
1. `git clone --recurse-submodules https://github.com/DFNCAP/echoview.git`
2. WINDOWS ONLY: Please read the README.me in `apple/README.md` to ensure you have the necessary Apple device drivers
3. Ensure `uv` is installed and available on the commandline.
4. `uv run build.py` -> This will fetch and install all necessary runtime dependencies.
5. `uv run -m app` -> This will run EchoView in a development environment. Note that `build.py` must have been run once to fetch the necessary runtime dependencies.


# Running on Linux
```bash
sudo apt install sudo apt install gstreamer1.0-plugins-base gstreamer1.0-libav gstreamer1.0-plugins-good gstreamer1.0-plugins-bad
```

## License
This project bundles go-ios (MIT) and scrcpy (Apache 2.0).
