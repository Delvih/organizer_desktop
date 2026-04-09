"""
Runtime helpers for locating bundled resources.
"""

import sys
from pathlib import Path


def get_project_root() -> Path:
    """Return the current project root or PyInstaller bundle root."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """Build an absolute path to a bundled resource."""
    return get_project_root().joinpath(*parts)
