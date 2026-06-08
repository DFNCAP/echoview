#!/usr/bin/env python3
"""Build script for EchoView using Nuitka."""

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

import click

from app.utils.install_thirdparty import install_msi, is_installed

BASE_DIR = Path(__file__).parent


def get_platform() -> str:
    """Get the current platform (Windows or Linux only)."""
    system = platform.system()
    if system == "Windows":
        return "Windows"
    elif system == "Linux":
        return "Linux"
    else:
        click.echo(
            f"Error: Unsupported platform {system}. Only Windows and Linux are supported.",
            err=True,
        )
        sys.exit(1)


def _sync_dependencies() -> None:
    """Sync dev and build dependencies using uv."""
    click.echo("Syncing dependencies...")

    # Sync dev dependencies
    result = subprocess.run(["uv", "sync", "--group", "dev"])
    if result.returncode != 0:
        click.echo("Error: Failed to sync dev dependencies.", err=True)
        sys.exit(1)

    # Sync build dependencies
    result = subprocess.run(["uv", "sync", "--group", "build"])
    if result.returncode != 0:
        click.echo("Error: Failed to sync build dependencies.", err=True)
        sys.exit(1)

    click.echo("Dependencies synced successfully.")


def _build_uxplay() -> None:
    platform = get_platform()
    if platform == "Windows":
        if not is_installed("Bonjour SDK"):
            print("Bonjour SDK not found, preparing to install")
            install_msi(BASE_DIR / "apple" / "BonjourSDK64.msi")
        script_path = Path("uxplay/build_uxplay_win.sh").resolve()
        subprocess.run(
            [r"C:\msys64\usr\bin\bash.exe", "-l", script_path],
            text=True,
            env={**os.environ, "MSYSTEM": "UCRT64", "CHERE_INVOKING": "1"},
        )
    else:
        script_path = Path("uxplay/build_uxplay_linux.sh").resolve()
        subprocess.run(script_path, text=True)


def download_file(url: str, dest: Path, chunk_size: int = 8192) -> None:
    """Download a file from a URL to a destination path with a progress indicator."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    with urllib.request.urlopen(url) as response:
        total = int(response.headers.get("Content-Length", 0))
        downloaded = 0

        with open(dest, "wb") as f:
            while chunk := response.read(chunk_size):
                f.write(chunk)
                downloaded += len(chunk)

                if total:
                    percent = downloaded / total * 100
                    filled = int(percent / 2)
                    bar = "█" * filled + "░" * (50 - filled)
                    print(
                        f"\r[{bar}] {percent:.1f}% ({downloaded}/{total} bytes)",
                        end="",
                        flush=True,
                    )

    print()  # newline after progress bar


def _download_go_ios() -> None:
    platform = get_platform()
    if platform == "Windows":
        url = "https://github.com/danielpaulus/go-ios/releases/download/v1.0.213/go-ios-win.zip"
        dest = Path("go-ios") / "go-ios-win-v1.0.213.zip"
    else:
        url = "https://github.com/danielpaulus/go-ios/releases/download/v1.0.213/go-ios-linux.zip"
        dest = Path("go-ios") / "go-ios-linux-v1.0.213.zip"

    download_file(url, dest)


def _download_scrcpy() -> None:
    platform = get_platform()
    if platform == "Windows":
        url = "https://github.com/Genymobile/scrcpy/releases/download/v4.0/scrcpy-win64-v4.0.zip"
        dest = Path("scrcpy") / "scrcpy-win64-v4.0.zip"
    else:
        url = "https://github.com/Genymobile/scrcpy/releases/download/v4.0/scrcpy-linux-x86_64-v4.0.tar.gz"
        dest = Path("scrcpy") / "scrcpy-linux-x86_64-v4.0.tar.gz"

    download_file(url, dest)


def _download_wintun() -> None:
    platform = get_platform()
    if platform == "Windows":
        url = "https://www.wintun.net/builds/wintun-0.14.1.zip"
        dest = Path("wintun") / "wintun-0.14.1.zip"
        download_file(url, dest)
    else:
        return


def _clean() -> None:
    """Clean build directory and scrcpy directory (keeping archives and git files)."""
    click.echo("Cleaning...")

    # Clean directories
    for dir_to_remove in ["build", ".mypy_cache", ".ruff_cache", "uxplay/UxPlay/build"]:
        path = Path(dir_to_remove)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
                click.echo(f"Removed {dir_to_remove}")

    # Clean all __pycache__ directories
    for pycache_dir in Path(".").rglob("__pycache__"):
        if pycache_dir.is_dir():
            shutil.rmtree(pycache_dir)
            click.echo(f"Removed {pycache_dir}")

    # Clean scrcpy directory
    scrcpy_dir = Path("scrcpy")
    if scrcpy_dir.exists():
        for item in scrcpy_dir.iterdir():
            # Keep git files and archives
            if item.name in [
                ".gitignore",
                ".keep",
                "LICENSE",
            ] or item.suffix in [
                ".gz",
                ".zip",
            ]:
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        click.echo(f"Cleaned {scrcpy_dir}")

    # Clean go-ios directory
    goios_dir = Path("go-ios")
    if goios_dir.exists():
        for item in goios_dir.iterdir():
            # Keep git files and archives
            if item.name in [
                ".gitignore",
                ".keep",
                "LICENSE",
            ] or item.suffix in [".zip"]:
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        click.echo(f"Cleaned {goios_dir}")

    # Clean go-ios directory
    wintun_dir = Path("wintun")
    if wintun_dir.exists():
        for item in wintun_dir.iterdir():
            # Keep git files and archives
            if item.name in [
                ".gitignore",
                ".keep",
                "LICENSE.txt",
            ] or item.suffix in [".zip"]:
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        click.echo(f"Cleaned {wintun_dir}")

    # Clean uxplay directory
    uxplay_dir = Path("uxplay")
    if uxplay_dir.exists():
        for item in uxplay_dir.iterdir():
            # Keep git files and archives
            if item.name in [".gitignore", ".keep"] or item.suffix in [
                ".zip",
                ".gz",
                ".sh",
            ]:
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        click.echo(f"Cleaned {uxplay_dir}")

    # Clean submodules
    uxplay_build_dir = Path("submodules/UxPlay/build")
    if uxplay_build_dir.exists():
        shutil.rmtree(uxplay_build_dir)
        click.echo(f"Cleaned {uxplay_build_dir}")


@click.command()
def build() -> None:
    """Build the application using Nuitka and rename the output directory."""
    platform = get_platform()
    _sync_dependencies()

    if platform == "Windows":
        uxplay_glob = "uxplay-win64-*.zip"
        scrcpy_glob = "scrcpy-win64-*.zip"
        go_ios_glob = "go-ios-win-*.zip"
    else:
        uxplay_glob = "uxplay-linux-*.tar.gz"
        scrcpy_glob = "scrcpy-linux-*.tar.gz"
        go_ios_glob = "go-ios-linux-*.zip"

    if not any(Path("go-ios").glob(go_ios_glob)):
        click.echo("Downloading go-ios")
        _download_go_ios()

    if platform == "Windows" and not any(Path("wintun").glob("wintun-*.zip")):
        click.echo("Downloading wintun")
        _download_wintun()

    if not any(Path("scrcpy").glob(scrcpy_glob)):
        click.echo("Downloading scrcpy")
        _download_scrcpy()

    if not any(Path("uxplay").glob(uxplay_glob)):
        click.echo("Building UxPlay")
        _build_uxplay()

    click.echo(f"Building EchoView for {platform}...")

    # Run Nuitka
    nuitka_cmd = [
        "uv",
        "run",
        "nuitka",
        "app",
    ]

    result = subprocess.run(nuitka_cmd)
    if result.returncode != 0:
        click.echo("Error: Nuitka build failed.", err=True)
        sys.exit(1)

    # Rename the output directory
    build_dir = Path("build")
    dist_dir = build_dir / "app.dist"
    target_dir = build_dir / "EchoView"

    if dist_dir.exists():
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.move(str(dist_dir), str(target_dir))
        click.echo(f"Build complete. Output: {target_dir}")

        # Archive the output directory
        if platform == "Linux":
            archive_path = build_dir / "EchoView-linux.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(target_dir, arcname="EchoView")
        else:
            archive_path = build_dir / "EchoView-win64.zip"
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in target_dir.rglob("*"):
                    if file.is_file():
                        zf.write(file, Path("EchoView") / file.relative_to(target_dir))
        click.echo(f"Archive created: {archive_path}")
    else:
        click.echo(f"Error: Expected output directory {dist_dir} not found.", err=True)
        sys.exit(1)


@click.command()
def run() -> None:
    """Run the application using uv run -m app."""
    click.echo("Running EchoView...")
    subprocess.run(["uv", "run", "-m", "app"])


@click.command()
def clean_all() -> None:
    _clean()
    for dir_to_remove in [".venv"]:
        path = Path(dir_to_remove)
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
                click.echo(f"Removed {dir_to_remove}")


@click.command()
def clean() -> None:
    _clean()


@click.group()
def cli() -> None:
    """Build script for EchoView."""
    pass


cli.add_command(build)
cli.add_command(run)
cli.add_command(clean)
cli.add_command(clean_all)


if __name__ == "__main__":
    if len(sys.argv) == 1:
        build()
    else:
        cli()
