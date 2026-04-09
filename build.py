#!/usr/bin/env python3
"""
build.py - Build standalone executables for FileOrganizer using PyInstaller.

Usage:
    python build.py           # Build for current platform
    python build.py --onefile # Single-file executable
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

ROOT = Path(__file__).parent


def check_pyinstaller():
    try:
        import PyInstaller
        return True
    except ImportError:
        print("PyInstaller not found. Install with:  pip install pyinstaller")
        return False


def build(onefile: bool = False):
    if not check_pyinstaller():
        sys.exit(1)

    args = [
        sys.executable, "-m", "PyInstaller",
        "--name", "FileOrganizer",
        "--windowed",                    # No console window
        "--clean",
        "--noconfirm",
        "--add-data", f"assets{os.pathsep}assets",
    ]

    if onefile:
        args.append("--onefile")
    else:
        args.append("--onedir")

    # Platform-specific icon
    icon_path = ROOT / "assets" / "icon"
    if sys.platform == "win32":
        ico = icon_path.with_suffix(".ico")
        if ico.exists():
            args += ["--icon", str(ico)]
    elif sys.platform == "darwin":
        icns = icon_path.with_suffix(".icns")
        if icns.exists():
            args += ["--icon", str(icns)]

    args.append(str(ROOT / "main.py"))

    print(f"Building FileOrganizer ({'onefile' if onefile else 'onedir'})...")
    result = subprocess.run(args, cwd=str(ROOT))
    if result.returncode == 0:
        print("\n✅ Build successful! Output is in the 'dist/' directory.")
    else:
        print("\n❌ Build failed.")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build FileOrganizer executable")
    parser.add_argument("--onefile", action="store_true", help="Create single-file executable")
    args = parser.parse_args()
    build(onefile=args.onefile)
