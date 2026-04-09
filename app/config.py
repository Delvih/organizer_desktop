"""
Configuration management for FileOrganizer.
"""

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_RULES: Dict[str, Dict[str, Any]] = {
    "Documents": {
        "extensions": [
            ".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".tex",
            ".md", ".csv", ".xls", ".xlsx", ".ppt", ".pptx", ".pages",
            ".numbers", ".key", ".epub", ".mobi",
        ],
        "color": "#4A90D9",
        "icon": "D",
        "enabled": True,
    },
    "Images": {
        "extensions": [
            ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp",
            ".tiff", ".tif", ".ico", ".heic", ".heif", ".raw", ".cr2",
            ".nef", ".arw", ".dng", ".psd", ".ai", ".eps",
        ],
        "color": "#E8A838",
        "icon": "I",
        "enabled": True,
    },
    "Videos": {
        "extensions": [
            ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
            ".m4v", ".mpeg", ".mpg", ".3gp", ".ogv", ".ts", ".vob",
            ".divx", ".xvid", ".rmvb",
        ],
        "color": "#E05C5C",
        "icon": "V",
        "enabled": True,
    },
    "Music": {
        "extensions": [
            ".mp3", ".flac", ".wav", ".aac", ".ogg", ".wma", ".m4a",
            ".aiff", ".alac", ".opus", ".mid", ".midi", ".amr",
        ],
        "color": "#9B59B6",
        "icon": "M",
        "enabled": True,
    },
    "Archives": {
        "extensions": [
            ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
            ".tar.gz", ".tar.bz2", ".tar.xz", ".iso", ".dmg", ".pkg",
            ".deb", ".rpm", ".cab",
        ],
        "color": "#1ABC9C",
        "icon": "A",
        "enabled": True,
    },
    "Executables": {
        "extensions": [
            ".exe", ".msi", ".app", ".apk", ".bat", ".sh", ".cmd",
            ".com", ".bin", ".run", ".jar", ".appimage",
        ],
        "color": "#E67E22",
        "icon": "E",
        "enabled": True,
    },
    "Code": {
        "extensions": [
            ".py", ".js", ".ts", ".html", ".css", ".java", ".cpp",
            ".c", ".h", ".cs", ".go", ".rs", ".rb", ".php", ".swift",
            ".kt", ".r", ".sql", ".json", ".xml", ".yaml", ".yml",
            ".toml", ".ini", ".cfg", ".conf",
        ],
        "color": "#2ECC71",
        "icon": "C",
        "enabled": True,
    },
    "Fonts": {
        "extensions": [".ttf", ".otf", ".woff", ".woff2", ".eot", ".fon"],
        "color": "#95A5A6",
        "icon": "F",
        "enabled": True,
    },
}

DEFAULT_CONFIG = {
    "watched_folders": [],
    "destination_folder": "",
    "rules": DEFAULT_RULES,
    "conflict_strategy": "rename",
    "run_on_startup": False,
    "minimize_to_tray": True,
    "log_level": "INFO",
    "organize_existing": False,
    "unknown_folder": "Misc",
    "unknown_enabled": True,
    "language": "en",
    "scan_interval": 30,
}


def get_config_path() -> Path:
    """Return the platform-specific config file path."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    config_dir = base / "FileOrganizer"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "config.json"


def get_log_path() -> Path:
    """Return the platform-specific log file path."""
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Logs"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    log_dir = base / "FileOrganizer"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "fileorganizer.log"


class Config:
    def __init__(self):
        self._path = get_config_path()
        self._data: Dict[str, Any] = {}
        self.load()

    def load(self):
        """Load config from disk, merging saved values with defaults."""
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._data = copy.deepcopy(DEFAULT_CONFIG)
                self._deep_merge(self._data, saved)
            except (json.JSONDecodeError, OSError):
                self._data = copy.deepcopy(DEFAULT_CONFIG)
        else:
            self._data = copy.deepcopy(DEFAULT_CONFIG)
            self.save()

    def save(self):
        """Persist config to disk."""
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    def get_rules(self) -> Dict[str, Dict[str, Any]]:
        return self._data.get("rules", {})

    def set_rules(self, rules: Dict[str, Dict[str, Any]]):
        self._data["rules"] = rules
        self.save()

    def get_extension_map(self) -> Dict[str, str]:
        """Build a flat extension-to-category lookup map."""
        ext_map: Dict[str, str] = {}
        for category, rule in self._data.get("rules", {}).items():
            if not rule.get("enabled", True):
                continue
            for ext in rule.get("extensions", []):
                ext_map[ext.lower()] = category
        return ext_map

    @property
    def watched_folders(self) -> List[str]:
        return self._data.get("watched_folders", [])

    @watched_folders.setter
    def watched_folders(self, folders: List[str]):
        self._data["watched_folders"] = folders
        self.save()

    @property
    def destination_folder(self) -> str:
        return self._data.get("destination_folder", "")

    @destination_folder.setter
    def destination_folder(self, path: str):
        self._data["destination_folder"] = path
        self.save()

    @property
    def conflict_strategy(self) -> str:
        return self._data.get("conflict_strategy", "rename")

    @conflict_strategy.setter
    def conflict_strategy(self, strategy: str):
        self._data["conflict_strategy"] = strategy
        self.save()

    @property
    def minimize_to_tray(self) -> bool:
        return self._data.get("minimize_to_tray", True)

    @property
    def unknown_folder(self) -> str:
        return self._data.get("unknown_folder", "Misc")

    @property
    def unknown_enabled(self) -> bool:
        return self._data.get("unknown_enabled", True)

    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
