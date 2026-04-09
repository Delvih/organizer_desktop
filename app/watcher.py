"""
watcher.py - Real-time filesystem monitoring using watchdog.
Watches multiple directories and triggers file organization on new files.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Callable, List, Set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

from .organizer import FileOrganizer, OrganizerResult
from .config import Config

logger = logging.getLogger("FileOrganizer")


class _OrganizerEventHandler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    """Watchdog event handler that organizes files on creation."""

    SETTLE_DELAY = 1.5  # seconds to wait for file write to complete

    def __init__(self, organizer: FileOrganizer, callback: Callable, watched_root: str):
        if WATCHDOG_AVAILABLE:
            super().__init__()
        self.organizer = organizer
        self.callback = callback
        self.watched_root = Path(watched_root)
        self._pending: Set[str] = set()
        self._lock = threading.Lock()

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and not event.is_directory:
            self._schedule(event.src_path)

    def on_moved(self, event):
        if isinstance(event, FileMovedEvent) and not event.is_directory:
            # File renamed/moved into the watched folder
            if Path(event.dest_path).parent.resolve() == self.watched_root.resolve():
                self._schedule(event.dest_path)

    def _schedule(self, path: str):
        """Delay processing to let the file finish writing."""
        with self._lock:
            if path in self._pending:
                return
            self._pending.add(path)

        def process():
            time.sleep(self.SETTLE_DELAY)
            with self._lock:
                self._pending.discard(path)
            if Path(path).exists():
                result = self.organizer.organize_file(path)
                if self.callback:
                    self.callback(result)

        t = threading.Thread(target=process, daemon=True)
        t.start()


class FolderWatcher:
    """Manages watchdog observers for multiple directories."""

    def __init__(self, config: Config, callback: Callable[[OrganizerResult], None] = None):
        self.config = config
        self.callback = callback
        self._organizer = FileOrganizer(config)
        self._observer: Observer = None
        self._running = False

    def is_available(self) -> bool:
        return WATCHDOG_AVAILABLE

    def start(self):
        if not WATCHDOG_AVAILABLE:
            logger.error("watchdog library not installed. Monitoring unavailable.")
            return False

        if self._running:
            self.stop()

        folders = self.config.watched_folders
        if not folders:
            logger.warning("No folders configured to watch.")
            return False

        self._observer = Observer()
        valid = 0
        for folder in folders:
            p = Path(folder)
            if not p.is_dir():
                logger.warning(f"Watch folder not found, skipping: {folder}")
                continue
            handler = _OrganizerEventHandler(self._organizer, self.callback, folder)
            self._observer.schedule(handler, str(p), recursive=False)
            logger.info(f"Watching: {folder}")
            valid += 1

        if valid == 0:
            logger.error("No valid folders to watch.")
            return False

        self._observer.start()
        self._running = True
        logger.info("File watcher started.")
        return True

    def stop(self):
        if self._observer and self._running:
            self._observer.stop()
            self._observer.join(timeout=3)
            self._running = False
            logger.info("File watcher stopped.")

    def restart(self):
        """Restart to pick up config changes."""
        self._organizer = FileOrganizer(self.config)
        self.stop()
        return self.start()

    @property
    def running(self) -> bool:
        return self._running

    def organize_existing(self) -> List[OrganizerResult]:
        """Organize all pre-existing files in watched folders."""
        results = []
        for folder in self.config.watched_folders:
            r = self._organizer.organize_folder(folder)
            results.extend(r)
        return results
