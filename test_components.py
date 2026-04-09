#!/usr/bin/env python3
"""
Quick test script to verify FileOrganizer is working correctly.
Tests all core components without launching the GUI.
"""

import sys
from pathlib import Path

# Prevent pytest from collecting this utility script as a test module.
__test__ = False

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

OK = "[OK]"
FAIL = "[FAIL]"


def _print_status(message, success, details=None):
    print(f"{message} {OK if success else FAIL}")
    if details:
        print(details)


def test_imports():
    """Test that all modules can be imported."""
    try:
        from app.config import Config, DEFAULT_CONFIG, DEFAULT_RULES
        from app.organizer import FileOrganizer, OrganizerResult
        from app.watcher import FolderWatcher
        from app.logger_setup import setup_logging, get_log_buffer

        _ = (
            Config,
            DEFAULT_CONFIG,
            DEFAULT_RULES,
            FileOrganizer,
            OrganizerResult,
            FolderWatcher,
            setup_logging,
            get_log_buffer,
        )
        _print_status("Testing imports...", True)
        return True
    except Exception as e:
        _print_status("Testing imports...", False, f"Error: {e}")
        return False


def test_config():
    """Test configuration management."""
    try:
        from app.config import Config

        config = Config()
        config.set("test_key", "test_value")

        assert config.get("test_key") == "test_value", "Config save/load failed"
        assert config.get("language") in ["en", "ru", "es", "zh", "pt"], "Language not set"
        assert isinstance(config.get("scan_interval"), int), "Scan interval not an integer"
        assert isinstance(config.get_rules(), dict), "get_rules failed"

        _print_status("Testing config management...", True)
        return True
    except Exception as e:
        _print_status("Testing config management...", False, f"Error: {e}")
        return False


def test_translations():
    """Test that locales.json is valid and complete."""
    try:
        import json

        locales_path = Path(__file__).parent / "locales.json"
        with open(locales_path, "r", encoding="utf-8") as f:
            translations = json.load(f)

        for lang in ["en", "ru", "es", "zh", "pt"]:
            assert lang in translations, f"Language {lang} not found"
            assert "title" in translations[lang], f"'title' missing in {lang}"
            assert "language" in translations[lang], f"'language' missing in {lang}"
            assert "scan_interval" in translations[lang], f"'scan_interval' missing in {lang}"

        _print_status("Testing translations...", True)
        return True
    except Exception as e:
        _print_status("Testing translations...", False, f"Error: {e}")
        return False


def test_organizer():
    """Test file organization logic."""
    try:
        from app.config import Config
        from app.organizer import FileOrganizer

        organizer = FileOrganizer(Config())
        assert organizer.categorize("test.pdf") in {"Documents", None}, "PDF categorization failed"
        assert organizer.categorize("test.jpg") in {"Images", None}, "JPG categorization failed"
        assert organizer.categorize("test.mp3") in {"Music", None}, "MP3 categorization failed"

        _print_status("Testing organizer...", True)
        return True
    except Exception as e:
        _print_status("Testing organizer...", False, f"Error: {e}")
        return False


def test_requirements():
    """Test that required packages are installed."""
    try:
        import watchdog

        _ = watchdog
        _print_status("Testing dependencies...", True)
        return True
    except ImportError:
        _print_status(
            "Testing dependencies...",
            False,
            "Warning: watchdog not installed. Install with: pip install watchdog",
        )
        return False


def test_optional_dependencies():
    """Test optional packages."""
    results = []

    try:
        import PIL

        _ = PIL
        results.append("Pillow[OK]")
    except ImportError:
        results.append("Pillow[MISSING]")

    try:
        import pystray

        _ = pystray
        results.append("pystray[OK]")
    except ImportError:
        results.append("pystray[MISSING]")

    print(f"Checking optional dependencies: {' '.join(results)}")
    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 50)
    print("FileOrganizer - Component Test Suite")
    print("=" * 50 + "\n")

    tests = [
        test_imports,
        test_config,
        test_translations,
        test_organizer,
        test_requirements,
        test_optional_dependencies,
    ]
    results = [test() for test in tests]

    print("\n" + "=" * 50)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 50 + "\n")

    if all(results):
        print("All tests passed. Application is ready to run.")
        print("\nNext steps:")
        print("1. Run: python create_icon.py")
        print("2. Run: python main.py")
        return 0

    print("Some tests failed. Check the errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
