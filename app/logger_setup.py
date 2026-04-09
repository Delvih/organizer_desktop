"""
logger_setup.py - Configures application-wide logging.
Outputs to both file and an in-memory ring buffer for the GUI log panel.
"""

import logging
import logging.handlers
from collections import deque
from typing import List
from .config import get_log_path


_LOG_BUFFER: deque = deque(maxlen=500)


class _BufferHandler(logging.Handler):
    """Stores log records in memory for the GUI to display."""
    def emit(self, record):
        msg = self.format(record)
        _LOG_BUFFER.append((record.levelname, msg))


def setup_logging(level: str = "INFO"):
    log_path = get_log_path()
    root = logging.getLogger("FileOrganizer")
    root.setLevel(getattr(logging, level, logging.INFO))

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                             datefmt="%Y-%m-%d %H:%M:%S")

    # Rotating file handler (5 MB × 3 backups)
    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)

    # In-memory buffer for GUI
    bh = _BufferHandler()
    bh.setFormatter(fmt)

    root.handlers.clear()
    root.addHandler(fh)
    root.addHandler(ch)
    root.addHandler(bh)

    return root


def get_log_buffer() -> List[tuple]:
    """Return a copy of buffered log entries as (level, message) tuples."""
    return list(_LOG_BUFFER)


def get_log_file_path() -> str:
    return str(get_log_path())
