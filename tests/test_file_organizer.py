import shutil
import threading
import time
from pathlib import Path

import pytest

import app.watcher as watcher


def test_categorize_case_insensitive(organizer, tmp_path):
    f = tmp_path / "example.TXT"
    f.write_text("hello", encoding="utf-8")
    assert organizer.categorize(str(f)) == "Documents"


def test_resolve_destination_unknown_disabled(organizer, config):
    config.set("unknown_enabled", False)
    cat, dest = organizer.resolve_destination("/some/path/file.unknownext")
    assert dest is None


def test_conflict_rename(organizer, config, tmp_path):
    # Setup source and existing destination
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    src = src_dir / "file.txt"
    src.write_text("a")

    config.destination_folder = str(tmp_path / "destroot")
    dest_folder = Path(config.destination_folder) / "Documents"
    dest_folder.mkdir(parents=True)
    (dest_folder / "file.txt").write_text("existing")

    res = organizer.organize_file(str(src))
    assert res.success is True
    assert res.action == "renamed"
    assert (dest_folder / "file (1).txt").exists()


def test_conflict_skip_and_overwrite(organizer, config, tmp_path):
    # Skip
    config.destination_folder = str(tmp_path / "d1")
    dest = Path(config.destination_folder) / "Documents"
    dest.mkdir(parents=True)
    # create a file in destination with same name as source to trigger conflict
    (dest / "a.txt").write_text("old")
    s = tmp_path / "a.txt"
    s.write_text("new")
    config.conflict_strategy = "skip"
    r = organizer.organize_file(str(s))
    assert r.action == "skipped"

    # Overwrite
    s2 = tmp_path / "src2.txt"
    s2.write_text("NEW")
    config.conflict_strategy = "overwrite"
    # place same name into dest
    (dest / "src2.txt").write_text("OLD")
    config.destination_folder = str(tmp_path / "d1")
    r2 = organizer.organize_file(str(s2))
    assert r2.success is True
    assert (dest / "src2.txt").read_text(encoding="utf-8") == "NEW"


def test_skip_hidden_and_temp(organizer, tmp_path):
    hidden = tmp_path / ".secret"
    hidden.write_text("x")
    r = organizer.organize_file(str(hidden))
    assert r.action == "skipped"

    tmpf = tmp_path / "notes.tmp"
    tmpf.write_text("x")
    r2 = organizer.organize_file(str(tmpf))
    assert r2.action == "skipped"


def test_organize_folder_moves_all_files(organizer, config, tmp_path):
    src = tmp_path / "many"
    src.mkdir()
    (src / "one.txt").write_text("1")
    (src / "two.jpg").write_text("2")
    (src / "noext").write_text("3")

    config.destination_folder = str(tmp_path / "destroot")
    results = organizer.organize_folder(str(src), dry_run=False)
    # three files processed (noext goes to Misc)
    assert len(results) == 3


def test_missing_source_returns_error(organizer):
    r = organizer.organize_file("/no/such/file.xyz")
    assert r.success is False
    assert r.action == "error"


def test_permission_error_handling(monkeypatch, organizer, tmp_path):
    s = tmp_path / "p.txt"
    s.write_text("x")

    def fake_move(a, b):
        raise PermissionError("denied")

    monkeypatch.setattr(shutil, "move", fake_move)
    r = organizer.organize_file(str(s))
    assert r.action == "error"
    assert "Permission denied" in r.message or "denied" in r.message


def test_unknown_no_extension(organizer, config, tmp_path):
    s = tmp_path / "file"
    s.write_text("x")
    config.destination_folder = str(tmp_path / "d")
    r = organizer.organize_file(str(s))
    assert r.success is True
    assert "Misc" in r.dst


def test_unicode_and_long_filename(organizer, config, tmp_path):
    uni = tmp_path / "файл_✓.pdf"
    uni.write_text("x")
    config.destination_folder = str(tmp_path / "d2")
    r = organizer.organize_file(str(uni))
    assert r.success is True

    long_name = "a" * 180 + ".txt"
    ln = tmp_path / long_name
    ln.write_text("x")
    r2 = organizer.organize_file(str(ln))
    assert r2.success is True


def test_watcher_handles_file_created(organizer, tmp_path):
    """Simulate watchdog FileCreatedEvent -> handler should call organizer and callback."""
    from app.watcher import _OrganizerEventHandler

    results = []
    done = threading.Event()

    def cb(r):
        results.append(r)
        done.set()

    handler = _OrganizerEventHandler(organizer, callback=cb, watched_root=str(tmp_path))

    p = tmp_path / "new.txt"
    p.write_text("x")

    Ev = watcher.FileCreatedEvent
    try:
        ev = Ev(str(p))
    except TypeError:
        ev = Ev()
        ev.src_path = str(p)
    ev.is_directory = False

    handler.on_created(ev)
    finished = done.wait(3)
    assert finished is True
    assert len(results) == 1
    assert results[0].success is True


def test_watcher_multiple_files(organizer, tmp_path):
    from app.watcher import _OrganizerEventHandler

    results = []
    done = threading.Event()
    target = 5

    def cb(r):
        results.append(r)
        if len(results) >= target:
            done.set()

    handler = _OrganizerEventHandler(organizer, callback=cb, watched_root=str(tmp_path))

    for i in range(target):
        p = tmp_path / f"file_{i}.txt"
        p.write_text("x")
        Ev = watcher.FileCreatedEvent
        try:
            ev = Ev(str(p))
        except TypeError:
            ev = Ev()
            ev.src_path = str(p)
        ev.is_directory = False
        handler.on_created(ev)

    ok = done.wait(5)
    assert ok is True
    assert len(results) == target


@pytest.mark.performance
def test_performance_dry_run(organizer, config, tmp_path):
    # Performance-oriented dry-run: create many small files and ensure quick processing
    src = tmp_path / "bulk"
    src.mkdir()
    n = 1000
    for i in range(n):
        (src / f"f{i}.txt").write_text("x")

    config.destination_folder = str(tmp_path / "perf_dest")
    t0 = time.time()
    results = organizer.organize_folder(str(src), dry_run=True)
    dt = time.time() - t0
    assert len(results) == n
    assert dt < 10.0
