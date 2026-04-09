#!/usr/bin/env python3
"""
Build standalone executables and a Windows self-extracting installer.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
INSTALLER_DIR = BUILD / "installer"
APP_NAME = "FileOrganizer"


def check_pyinstaller() -> bool:
    try:
        import PyInstaller  # noqa: F401
        return True
    except ImportError:
        print("PyInstaller not found. Install with: pip install pyinstaller")
        return False


def ensure_assets():
    assets_dir = ROOT / "assets"
    png_icon = assets_dir / "icon.png"
    ico_icon = assets_dir / "icon.ico"
    if png_icon.exists() and ico_icon.exists():
        return

    print("Generating application icons...")
    result = subprocess.run([sys.executable, str(ROOT / "create_icon.py")], cwd=str(ROOT))
    if result.returncode != 0:
        raise SystemExit("Icon generation failed.")


def run_pyinstaller(onefile: bool = False):
    if not check_pyinstaller():
        raise SystemExit(1)

    ensure_assets()

    args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name",
        APP_NAME,
        "--windowed",
        "--clean",
        "--noconfirm",
        "--collect-submodules",
        "pystray",
        "--add-data",
        f"locales.json{os.pathsep}.",
        "--add-data",
        f"assets{os.pathsep}assets",
    ]

    if onefile:
        args.append("--onefile")
    else:
        args.append("--onedir")

    ico_path = ROOT / "assets" / "icon.ico"
    if sys.platform == "win32" and ico_path.exists():
        args += ["--icon", str(ico_path)]

    args.append(str(ROOT / "main.py"))

    print(f"Building {APP_NAME} ({'onefile' if onefile else 'onedir'})...")
    result = subprocess.run(args, cwd=str(ROOT))
    if result.returncode != 0:
        raise SystemExit("PyInstaller build failed.")

    print("Executable build successful.")


def write_installer_scripts():
    INSTALLER_DIR.mkdir(exist_ok=True)

    (INSTALLER_DIR / "setup.ps1").write_text(
        "$appDir = Join-Path $env:LOCALAPPDATA 'Programs\\FileOrganizer'\n"
        "New-Item -ItemType Directory -Force -Path $appDir | Out-Null\n"
        "Copy-Item -Force 'FileOrganizer.exe' (Join-Path $appDir 'FileOrganizer.exe')\n"
        "Copy-Item -Force 'README.txt' (Join-Path $appDir 'README.txt')\n"
        "$shell = New-Object -ComObject WScript.Shell\n"
        "$desktopShortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'FileOrganizer.lnk'))\n"
        "$desktopShortcut.TargetPath = Join-Path $appDir 'FileOrganizer.exe'\n"
        "$desktopShortcut.WorkingDirectory = $appDir\n"
        "$desktopShortcut.Save()\n"
        "$menuShortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('StartMenu')) 'Programs\\FileOrganizer.lnk'))\n"
        "$menuShortcut.TargetPath = Join-Path $appDir 'FileOrganizer.exe'\n"
        "$menuShortcut.WorkingDirectory = $appDir\n"
        "$menuShortcut.Save()\n"
        "Start-Process -FilePath (Join-Path $appDir 'FileOrganizer.exe')\n",
        encoding="utf-8",
    )

    (INSTALLER_DIR / "setup.cmd").write_text(
        "@echo off\n"
        "setlocal\n"
        "cd /d \"%~dp0\"\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -File \"%~dp0setup.ps1\"\n"
        "exit /b %errorlevel%\n",
        encoding="utf-8",
    )

    (INSTALLER_DIR / "README.txt").write_text(
        "FileOrganizer\r\n\r\n"
        "Installed to %LOCALAPPDATA%\\Programs\\FileOrganizer.\r\n"
        "Use the desktop or Start Menu shortcut to launch the app.\r\n",
        encoding="utf-8",
    )


def write_iexpress_sed(target_name: Path) -> Path:
    sed_path = INSTALLER_DIR / "FileOrganizerInstaller.sed"
    source_dir = Path(tempfile.gettempdir())
    target_name = target_name.resolve()

    sed_path.write_text(
        "[Version]\n"
        "Class=IEXPRESS\n"
        "SEDVersion=3\n"
        "[Options]\n"
        "PackagePurpose=InstallApp\n"
        "ShowInstallProgramWindow=1\n"
        "HideExtractAnimation=0\n"
        "UseLongFileName=1\n"
        "InsideCompressed=0\n"
        "CAB_FixedSize=0\n"
        "CAB_ResvCodeSigning=0\n"
        "RebootMode=N\n"
        "InstallPrompt=\n"
        "DisplayLicense=\n"
        "FinishMessage=FileOrganizer installation completed.\n"
        f"TargetName={target_name}\n"
        "FriendlyName=FileOrganizer Installer\n"
        "AppLaunched=setup.cmd\n"
        "PostInstallCmd=<None>\n"
        "AdminQuietInstCmd=setup.cmd\n"
        "UserQuietInstCmd=setup.cmd\n"
        "SourceFiles=SourceFiles\n"
        "[Strings]\n"
        "FILE0=setup.cmd\n"
        "FILE1=FileOrganizer.exe\n"
        "FILE2=README.txt\n"
        "FILE3=setup.ps1\n"
        "[SourceFiles]\n"
        f"SourceFiles0={source_dir}\n"
        "[SourceFiles0]\n"
        "%FILE0%=\n"
        "%FILE1%=\n"
        "%FILE2%=\n"
        "%FILE3%=\n",
        encoding="utf-8",
    )
    return sed_path


def build_installer():
    exe_path = DIST / f"{APP_NAME}.exe"
    if not exe_path.exists():
        raise SystemExit(f"Portable executable not found: {exe_path}")

    write_installer_scripts()

    staging_dir = Path(tempfile.mkdtemp(prefix="fileorganizer-installer-", dir=BUILD))

    shutil.copy2(exe_path, staging_dir / exe_path.name)
    shutil.copy2(INSTALLER_DIR / "setup.cmd", staging_dir / "setup.cmd")
    shutil.copy2(INSTALLER_DIR / "README.txt", staging_dir / "README.txt")
    shutil.copy2(INSTALLER_DIR / "setup.ps1", staging_dir / "setup.ps1")

    target_name = DIST / f"{APP_NAME}-Setup.exe"
    sed_path = write_iexpress_sed(target_name)
    sed_text = sed_path.read_text(encoding="utf-8")
    sed_text = sed_text.replace(str(Path(tempfile.gettempdir()).resolve()), str(staging_dir.resolve()))
    sed_path.write_text(sed_text, encoding="utf-8")

    iexpress = Path(os.environ["SystemRoot"]) / "System32" / "iexpress.exe"
    print(f"Building Windows installer: {target_name.name}")
    result = subprocess.run([str(iexpress), "/N", str(sed_path)], cwd=str(ROOT))
    if result.returncode != 0:
        raise SystemExit("IExpress installer build failed.")

    print("Installer build successful.")


def main():
    parser = argparse.ArgumentParser(description="Build FileOrganizer deliverables")
    parser.add_argument("--onefile", action="store_true", help="Create a single-file executable")
    parser.add_argument(
        "--installer",
        action="store_true",
        help="Build a Windows self-extracting installer after the executable build",
    )
    args = parser.parse_args()

    run_pyinstaller(onefile=args.onefile)
    if args.installer:
        build_installer()


if __name__ == "__main__":
    main()
