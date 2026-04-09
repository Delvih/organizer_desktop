from types import SimpleNamespace

import pytest

from app.gui import FileOrganizerApp
from app.config import Config


def test_save_destination(config, tmp_path):
    dummy = SimpleNamespace(config=config, _dest_var=SimpleNamespace(get=lambda: str(tmp_path)))
    FileOrganizerApp._save_dest(dummy)
    assert config.destination_folder == str(tmp_path)


def test_add_and_remove_watch_folder(monkeypatch, config, tmp_path):
    # Simulate filedialog returning the chosen folder
    import tkinter.filedialog as fd

    monkeypatch.setattr(fd, "askdirectory", lambda title=None: str(tmp_path))

    dummy = SimpleNamespace(
        config=config,
        _refresh_folder_list=lambda: None,
        watcher=SimpleNamespace(running=False, restart=lambda: None),
    )

    # Add
    FileOrganizerApp._add_watch_folder(dummy)
    assert str(tmp_path) in config.watched_folders

    # Remove
    FileOrganizerApp._remove_folder(dummy, str(tmp_path))
    assert str(tmp_path) not in config.watched_folders


def test_toggle_rule_and_delete(monkeypatch, config):
    # Prepare a custom rule
    rules = config.get_rules()
    rules["TempCat"] = {"extensions": [".tmp"], "enabled": True}
    config.set_rules(rules)

    dummy = SimpleNamespace(config=config)

    # Toggle off
    FileOrganizerApp._toggle_rule(dummy, "TempCat", False)
    assert config.get_rules()["TempCat"]["enabled"] is False

    # Delete (confirm via messagebox)
    import tkinter.messagebox as mb
    monkeypatch.setattr(mb, "askyesno", lambda *a, **k: True)
    dummy._render_rules = lambda: None
    FileOrganizerApp._delete_category(dummy, "TempCat")
    assert "TempCat" not in config.get_rules()


def test_toggle_watcher_starts(monkeypatch, config):
    # Ensure there is at least one watched folder
    config.watched_folders = ["/tmp/watch-me"]

    started = {"flag": False}

    class FakeWatcher:
        def __init__(self):
            self.running = False

        def is_available(self):
            return True

        def start(self):
            started["flag"] = True
            self.running = True
            return True

        def stop(self):
            self.running = False

        def restart(self):
            self.running = True

    dummy = SimpleNamespace(
        config=config,
        watcher=FakeWatcher(),
        _update_watcher_ui=lambda x: None,
        _navigate=lambda p: None,
    )

    # Should start without raising
    FileOrganizerApp._toggle_watcher(dummy)
    assert started["flag"] is True
