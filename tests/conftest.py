import os
import threading
from types import SimpleNamespace
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_config(tmp_path, monkeypatch):
    """Isolate config/log paths to tmp_path for all tests (autouse).
    This prevents touching user home / APPDATA during tests.
    """
    import app.config as config_mod
    import app.logger_setup as logger_setup_mod

    cfg_file = tmp_path / "config.json"
    log_file = tmp_path / "fileorganizer.log"

    monkeypatch.setattr(config_mod, "get_config_path", lambda: cfg_file)
    monkeypatch.setattr(config_mod, "get_log_path", lambda: log_file)

    # logger_setup imported get_log_path at import-time; patch the accessor used by GUI
    monkeypatch.setattr(logger_setup_mod, "get_log_file_path", lambda: str(log_file))

    yield


@pytest.fixture
def config():
    """Return a fresh Config instance (uses patched get_config_path)."""
    from app.config import Config

    return Config()


@pytest.fixture
def organizer(config):
    """Return a FileOrganizer bound to the temp config."""
    from app.organizer import FileOrganizer

    return FileOrganizer(config)


@pytest.fixture(autouse=True)
def reduce_watcher_delay(monkeypatch):
    """Speed up watcher tests and ensure event classes exist.
    Makes the internal settle delay zero to avoid long sleeps.
    """
    import app.watcher as watcher_mod

    # Reduce settle delay to make tests deterministic and fast
    try:
        watcher_mod._OrganizerEventHandler.SETTLE_DELAY = 0
    except AttributeError:
        pass

    yield


def create_file(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def create_file_fixture(tmp_path):
    return lambda relpath, content="x": create_file(tmp_path / relpath, content)
