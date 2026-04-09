#!/usr/bin/env python3
"""
Build standalone executables and a Windows self-extracting installer.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
INSTALLER_DIR = ROOT / "installer"
STAGING_DIR = BUILD / "installer_staging"
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

    (INSTALLER_DIR / "setup.cmd").write_text(
        "@echo off\n"
        "setlocal\n"
        "set \"APP_DIR=%LOCALAPPDATA%\\Programs\\FileOrganizer\"\n"
        "mkdir \"%APP_DIR%\" 2>nul\n"
        "copy /Y \"FileOrganizer.exe\" \"%APP_DIR%\\FileOrganizer.exe\" >nul\n"
        "copy /Y \"README.txt\" \"%APP_DIR%\\README.txt\" >nul\n"
        "powershell -NoProfile -ExecutionPolicy Bypass -Command "
        "\"$s=New-Object -ComObject WScript.Shell;"
        "$desktop=$s.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\\FileOrganizer.lnk');"
        "$desktop.TargetPath=$env:LOCALAPPDATA + '\\Programs\\FileOrganizer\\FileOrganizer.exe';"
        "$desktop.WorkingDirectory=$env:LOCALAPPDATA + '\\Programs\\FileOrganizer';$desktop.Save();"
        "$menu=$s.CreateShortcut([Environment]::GetFolderPath('StartMenu') + '\\Programs\\FileOrganizer.lnk');"
        "$menu.TargetPath=$env:LOCALAPPDATA + '\\Programs\\FileOrganizer\\FileOrganizer.exe';"
        "$menu.WorkingDirectory=$env:LOCALAPPDATA + '\\Programs\\FileOrganizer';$menu.Save()\"\n"
        "start \"\" \"%APP_DIR%\\FileOrganizer.exe\"\n"
        "exit /b 0\n",
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
    source_dir = STAGING_DIR.resolve()
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
        "[SourceFiles]\n"
        f"SourceFiles0={source_dir}\n"
        "[SourceFiles0]\n"
        "%FILE0%=\n"
        "%FILE1%=\n"
        "%FILE2%=\n",
        encoding="utf-8",
    )
    return sed_path


def build_installer():
    exe_path = DIST / f"{APP_NAME}.exe"
    if not exe_path.exists():
        raise SystemExit(f"Portable executable not found: {exe_path}")

    write_installer_scripts()

    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True)

    shutil.copy2(exe_path, STAGING_DIR / exe_path.name)
    shutil.copy2(INSTALLER_DIR / "setup.cmd", STAGING_DIR / "setup.cmd")
    shutil.copy2(INSTALLER_DIR / "README.txt", STAGING_DIR / "README.txt")

    target_name = DIST / f"{APP_NAME}-Setup.exe"
    sed_path = write_iexpress_sed(target_name)

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
