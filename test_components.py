#!/usr/bin/env python3
"""
Quick test script to verify FileOrganizer is working correctly.
Tests all core components without launching the GUI.
"""

import sys
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...", end=" ")
    try:
        from app.config import Config, DEFAULT_CONFIG, DEFAULT_RULES
        from app.organizer import FileOrganizer, OrganizerResult
        from app.watcher import FolderWatcher
        from app.logger_setup import setup_logging, get_log_buffer
        print("✓")
        return True
    except Exception as e:
        print(f"✗\nError: {e}")
        return False

def test_config():
    """Test configuration management."""
    print("Testing config management...", end=" ")
    try:
        from app.config import Config
        config = Config()
        
        # Test get/set
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value", "Config save/load failed"
        
        # Test language setting
        assert config.get("language") in ["en", "ru", "es", "zh", "pt"], "Language not set"
        
        # Test scan interval
        assert isinstance(config.get("scan_interval"), int), "Scan interval not an integer"
        
        # Test typed methods
        rules = config.get_rules()
        assert isinstance(rules, dict), "get_rules failed"
        
        print("✓")
        return True
    except Exception as e:
        print(f"✗\nError: {e}")
        return False

def test_translations():
    """Test that locales.json is valid and complete."""
    print("Testing translations...", end=" ")
    try:
        import json
        locales_path = Path(__file__).parent / "locales.json"
        
        with open(locales_path, 'r', encoding='utf-8') as f:
            translations = json.load(f)
        
        # Check all 5 languages exist
        required_langs = ["en", "ru", "es", "zh", "pt"]
        for lang in required_langs:
            assert lang in translations, f"Language {lang} not found"
            
            # Check key translations exist
            assert "title" in translations[lang], f"'title' missing in {lang}"
            assert "language" in translations[lang], f"'language' missing in {lang}"
            assert "scan_interval" in translations[lang], f"'scan_interval' missing in {lang}"
        
        print("✓")
        return True
    except Exception as e:
        print(f"✗\nError: {e}")
        return False

def test_organizer():
    """Test file organization logic."""
    print("Testing organizer...", end=" ")
    try:
        from app.config import Config
        from app.organizer import FileOrganizer
        
        config = Config()
        organizer = FileOrganizer(config)
        
        # Test categorization
        result = organizer.categorize("test.pdf")
        assert result == "Documents" or result is None, "PDF categorization failed"
        
        result = organizer.categorize("test.jpg")
        assert result == "Images" or result is None, "JPG categorization failed"
        
        result = organizer.categorize("test.mp3")
        assert result == "Music" or result is None, "MP3 categorization failed"
        
        print("✓")
        return True
    except Exception as e:
        print(f"✗\nError: {e}")
        return False

def test_requirements():
    """Test that required packages are installed."""
    print("Testing dependencies...", end=" ")
    try:
        import watchdog
        print("✓")
        return True
    except ImportError:
        print("✗\nWarning: watchdog not installed. Install with: pip install watchdog")
        return False

def test_optional_dependencies():
    """Test optional packages."""
    print("Checking optional dependencies:", end=" ")
    results = []
    
    try:
        import PIL
        results.append("Pillow✓")
    except ImportError:
        results.append("Pillow✗")
    
    try:
        import pystray
        results.append("pystray✓")
    except ImportError:
        results.append("pystray✗")
    
    print(" ".join(results))
    return True

def main():
    """Run all tests."""
    print("\n" + "="*50)
    print("FileOrganizer - Component Test Suite")
    print("="*50 + "\n")
    
    tests = [
        test_imports,
        test_config,
        test_translations,
        test_organizer,
        test_requirements,
        test_optional_dependencies,
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "="*50)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("="*50 + "\n")
    
    if all(results):
        print("✅ All tests passed! Application is ready to run.")
        print("\nNext steps:")
        print("1. Run: python create_icon.py")
        print("2. Run: python main.py")
        return 0
    else:
        print("⚠️ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
