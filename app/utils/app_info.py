import importlib.metadata
import os
import platform
import subprocess
import sys
from pathlib import Path

from platformdirs import PlatformDirs


class AppInfo:
    """
    Singleton class that provides information about the application and its related directories.

    This class encapsulates metadata about the application and provides properties to
    access important directories such as user data and log folders. The directories are determined
    using the `platformdirs` package, ensuring platform-specific conventions are adhered to.

    Examples:
        >>> print(app_info.app_name)
        >>> print(app_info.app_storage_folder)
    """

    _instance: "None | AppInfo" = None

    def __new__(cls) -> "AppInfo":
        """
        Create a new instance or return the existing singleton instance of the `AppInfo` class.
        """
        if cls._instance is None:
            cls._instance = super(AppInfo, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """
        Initialize the `AppInfo` instance, setting application metadata and determining important directories.

        Raises:
            Exception: If the main file path cannot be determined.
        """
        if hasattr(self, "_is_initialized") and self._is_initialized:
            return

        main_file = sys.modules["__main__"].__file__

        if main_file is None:
            raise Exception("Unable to get the main file path.")

        # Need to go one up if we are running from source
        self._application_folder = (
            Path(main_file).resolve().parent
            if "__compiled__" in globals()
            # __compiled__ will be present if Nuitka has frozen this
            else Path(main_file).resolve().parent.parent
        )

        # Application metadata
        self._app_name = "EchoView"
        self._app_copyright = ""

        self._app_version = self._resolve_version()

        # Define important directories using platformdirs
        platform_dirs = PlatformDirs(appname=self._app_name, appauthor=False)
        self._app_storage_folder = platform_dirs.user_data_path
        self._user_log_folder = platform_dirs.user_log_path

        # Derive some secondary directory paths
        self._settings_file: Path = self._app_storage_folder / "settings.json"

        # Backup directories

        # Make sure important directories exist
        self._app_storage_folder.mkdir(parents=True, exist_ok=True)
        self._user_log_folder.mkdir(parents=True, exist_ok=True)

        # Create backup directories

        self._is_initialized: bool = True

    def _resolve_version(self) -> str:
        """Resolve application version from generated file, git, or package metadata."""
        # 1. Nuitka / standalone builds with baked-in _version.py
        try:
            from app._version import VERSION  # type: ignore[reportMissingImports]

            return VERSION
        except Exception:
            pass

        # 2. Running from source with git available (live, before cached package metadata)
        try:
            describe = subprocess.run(
                ["git", "describe", "--tags"],
                capture_output=True,
                text=True,
                cwd=self._application_folder,
                check=True,
            ).stdout.strip()

            parts = describe.rsplit("-", 2)
            if len(parts) == 1:
                tag = parts[0]
                version = tag
            else:
                tag, distance, commit = parts
                commit = commit.lstrip("g")
                version = f"{tag}+{distance}+{commit}"

            dirty = (
                subprocess.run(
                    ["git", "diff-index", "--quiet", "HEAD", "--"],
                    capture_output=True,
                    cwd=self._application_folder,
                ).returncode
                != 0
            )
            if dirty:
                version += ".dirty"

            return version
        except Exception:
            pass

        # 3. Installed package (uv run after sync, pip install, etc.)
        try:
            return importlib.metadata.version("echoview")
        except Exception:
            pass

        return "Unknown version"

    @property
    def adb_path(self) -> Path:
        """Get the path to the ADB executable."""
        system = platform.system()
        if system == "Windows":
            return self._application_folder / "scrcpy" / "adb.exe"
        else:
            return self._application_folder / "scrcpy" / "adb"

    @property
    def scrcpy_path(self) -> Path:
        """Get the path to the scrcpy executable."""
        system = platform.system()
        if system == "Windows":
            return self._application_folder / "scrcpy" / "scrcpy.exe"
        else:
            return self._application_folder / "scrcpy" / "scrcpy"

    @property
    def goios_path(self) -> Path:
        """Get the path to the scrcpy executable."""
        system = platform.system()
        if system == "Windows":
            return self._application_folder / "go-ios" / "ios.exe"
        else:
            return self._application_folder / "go-ios" / "ios-amd64"

    @property
    def uxplay_path(self) -> Path:
        """Get the path to the scrcpy executable."""
        system = platform.system()
        if system == "Windows":
            return self._application_folder / "uxplay" / "bin" / "uxplay.exe"
        else:
            return self._application_folder / "uxplay" / "bin" / "uxplay"

    @property
    def app_name(self) -> str:
        """
        Get the name of the application.

        Returns:
            str: The name of the application.
        """
        return self._app_name

    @property
    def app_version(self) -> str:
        """
        Get the application version string.

        Returns:
            str: The version of the application.
        """
        return self._app_version

    @property
    def app_copyright(self) -> str:
        """
        Get the copyright information for the application.

        Returns:
            str: The copyright information for the application.
        """
        return self._app_copyright

    @property
    def application_folder(self) -> Path:
        """
        Get the path to the folder where the main application file resides.

        Returns:
            Path: The path to the application's main folder.
        """
        return self._application_folder

    @property
    def app_storage_folder(self) -> Path:
        """
        Get the path to the folder where user-specific data for the application is stored.

        This directory is determined using platform-specific conventions.

        Returns:
            Path: The path to the user-specific data folder.
        """
        return self._app_storage_folder

    @property
    def app_settings_file(self) -> Path:
        """
        Get the path to the file where user-specific data for the application is stored.

        This directory is determined using platform-specific conventions.

        Returns:
            Path: The path to the user-specific data file.
        """
        return self._settings_file

    @property
    def user_log_folder(self) -> Path:
        """
        Get the path to the folder where application logs are stored for the user.

        This directory is determined using platform-specific conventions.

        Returns:
            Path: The path to the user-specific log folder.
        """
        return self._user_log_folder
