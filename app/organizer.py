"""
Core file organization logic.
"""

import logging
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Set, Tuple

from .config import Config


logger = logging.getLogger("FileOrganizer")

# ---------------------------------------------------------------------------
# Blacklist — exact folder names that are ALWAYS system-critical.
# We match these against individual path components (case-insensitive).
# Keep this list tight: only names that are *exclusively* system folders.
# ---------------------------------------------------------------------------
_BLACKLIST_EXACT: Set[str] = {
    "windows",
    "program files",
    "program files (x86)",
    "system32",
    "syswow64",
    "programdata",
    "system volume information",
    "$recycle.bin",
}

# These names are only dangerous when they appear directly under "appdata".
# "local" and "roaming" are common English words — do NOT block them globally.
_BLACKLIST_UNDER_APPDATA: Set[str] = {"local", "roaming", "localappdata"}


def _is_path_blacklisted(path: Path) -> bool:
    """
    Return True if *path* is inside a protected system folder.

    Rules (in order):
    1. Any component exactly matches a top-level system name (windows, system32 …)
    2. "local" / "roaming" only when they sit directly under "appdata"
    3. Any component starts with a dot  →  hidden directory
    4. Windows FILE_ATTRIBUTE_SYSTEM flag on the directory itself
    """
    parts = [p.lower().rstrip("\\/") for p in path.parts]

    for i, part in enumerate(parts):
        # Rule 1 — unconditional system names
        if part in _BLACKLIST_EXACT:
            return True

        # Rule 2 — "local"/"roaming" only under AppData
        if part in _BLACKLIST_UNDER_APPDATA:
            if i > 0 and parts[i - 1] == "appdata":
                return True

        # Rule 3 — hidden dirs (dot-prefix), skip "." and ".."
        if part.startswith(".") and part not in (".", ".."):
            return True

    # Rule 4 — Windows FILE_ATTRIBUTE_SYSTEM (0x4)
    # Only apply outside the user's home directory.
    # On localised Windows (Russian, Chinese, etc.) user shell folders like
    # Загрузки / Документы can carry FILE_ATTRIBUTE_READONLY or even
    # FILE_ATTRIBUTE_SYSTEM as a shell-namespace hint — we must not block them.
    if os.name == "nt":
        try:
            home = Path.home()
            path.relative_to(home)   # raises ValueError if NOT under home
            # Path is inside the user's home — skip the system-attribute check.
        except ValueError:
            # Path is outside home → apply the check
            try:
                attrs = os.stat(path).st_file_attributes  # type: ignore[attr-defined]
                if attrs & 0x4:  # FILE_ATTRIBUTE_SYSTEM
                    return True
            except (OSError, AttributeError):
                pass

    return False


# ---------------------------------------------------------------------------
# Global set of file paths currently being organised.
# Prevents the watcher and the periodic scan from organising the same file
# simultaneously (race condition → double-move → FileNotFoundError).
# ---------------------------------------------------------------------------
_IN_PROGRESS: Set[str] = set()
_IN_PROGRESS_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Windows: read actual user-folder paths from the registry.
# This is language-independent — works on English, Russian, Chinese, etc.
# "Documents" on a Russian install is actually "Документы" on disk; the
# registry always stores the real filesystem path, not the display name.
# ---------------------------------------------------------------------------
# Registry key → human-readable category used by this app
_WIN_SHELL_FOLDER_KEYS = {
    "Personal":                                       "Documents",
    "My Pictures":                                    "Images",
    "My Video":                                       "Videos",
    "My Music":                                       "Music",
    "{374DE290-123F-4565-9164-39C4925E467B}":         "Downloads",
}

def _win_user_folders() -> dict:
    """
    Return {category: Path} for well-known Windows user folders,
    read from the registry so they are correct regardless of UI language.
    Returns an empty dict on non-Windows or if the registry is unavailable.
    """
    if os.name != "nt":
        return {}
    result: dict = {}
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        for reg_name, category in _WIN_SHELL_FOLDER_KEYS.items():
            try:
                raw, _ = winreg.QueryValueEx(key, reg_name)
                # Expand %USERPROFILE%, %APPDATA%, … that Windows stores literally
                expanded = os.path.expandvars(raw)
                result[category] = Path(expanded)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
    except Exception as exc:
        logger.debug(f"Could not read user shell folders from registry: {exc}")
    return result


# Cache so we don't hit the registry on every file operation
_WIN_FOLDERS_CACHE: Optional[dict] = None
_WIN_FOLDERS_LOCK = threading.Lock()


def _get_win_user_folder(category: str) -> Optional[Path]:
    """Return the actual (localised) path for a well-known user folder."""
    global _WIN_FOLDERS_CACHE
    with _WIN_FOLDERS_LOCK:
        if _WIN_FOLDERS_CACHE is None:
            _WIN_FOLDERS_CACHE = _win_user_folders()
    return _WIN_FOLDERS_CACHE.get(category)


class OrganizerResult:
    def __init__(self, success: bool, src: str, dst: str, action: str, message: str = ""):
        self.success = success
        self.src = src
        self.dst = dst
        self.action = action  # moved | skipped | error | renamed
        self.message = message
        self.timestamp = datetime.now()

    def __repr__(self):
        return f"[{self.action.upper()}] {Path(self.src).name} -> {self.dst} | {self.message}"


class FileOrganizer:
    def __init__(self, config: Config):
        self.config = config

    def categorize(self, filepath: str) -> Optional[str]:
        """Return the category name for a file, or None if unknown."""
        ext = Path(filepath).suffix.lower()
        ext_map = self.config.get_extension_map()
        return ext_map.get(ext)

    def get_category_root(self, category: str) -> Path:
        """
        Return the root folder for a category.

        Priority:
        1. Manually configured destination root (user set it explicitly)
        2. Windows registry  → actual localised path (Документы, Изображения …)
        3. Hardcoded English fallback (non-Windows or registry unavailable)
        """
        if self.config.destination_folder:
            return Path(self.config.destination_folder) / category

        # Try Windows registry first — language-independent, always correct
        win_folder = _get_win_user_folder(category)
        if win_folder is not None:
            return win_folder

        # Fallback for non-Windows or registry miss
        fallback = {
            "Documents": Path.home() / "Documents",
            "Images":    Path.home() / "Pictures",
            "Videos":    Path.home() / "Videos",
            "Music":     Path.home() / "Music",
        }
        return fallback.get(category, Path.home() / "Documents" / "FileOrganizer" / category)

    def build_destination_path(self, filepath: str, category: str) -> Path:
        """
        Build the final destination path for a file.
        Files are stored inside a folder named after the file stem.
        """
        src = Path(filepath)
        category_root = self.get_category_root(category)
        wrapper_folder = category_root / src.stem
        return wrapper_folder / src.name

    def resolve_destination(self, filepath: str) -> Tuple[str, Optional[str]]:
        """
        Determine where a file should go.
        Returns (category_name_or_unknown, destination_file_path).
        """
        category = self.categorize(filepath)
        if category is None:
            if self.config.unknown_enabled:
                category = self.config.unknown_folder
            else:
                return ("", None)

        dest_path = self.build_destination_path(filepath, category)
        return (category, str(dest_path))

    def _handle_conflict(self, dest_path: Path) -> Optional[Path]:
        """
        Handle file naming conflicts based on the configured strategy.
        Returns the new path, or None if the file should be skipped.
        """
        strategy = self.config.conflict_strategy
        if strategy == "skip":
            return None
        if strategy == "overwrite":
            return dest_path

        stem = dest_path.stem
        suffix = dest_path.suffix
        parent = dest_path.parent
        counter = 1
        while True:
            new_name = f"{stem} ({counter}){suffix}"
            new_path = parent / new_name
            if not new_path.exists():
                return new_path
            counter += 1

    def organize_file(self, filepath: str, dry_run: bool = False) -> OrganizerResult:
        """
        Move a single file through the organization pipeline.
        1. Detect category
        2. Select category root folder
        3. Save the file inside its own wrapper folder

        Thread-safe: uses a global in-progress set so the watcher and the
        periodic scan never process the same file simultaneously.
        """
        src = Path(filepath)
        src_key = str(src.resolve())

        # ── race-condition guard ─────────────────────────────────────────────
        with _IN_PROGRESS_LOCK:
            if src_key in _IN_PROGRESS:
                return OrganizerResult(
                    False, filepath, "", "skipped",
                    "Already being processed by another thread"
                )
            _IN_PROGRESS.add(src_key)

        try:
            return self._organize_file_inner(src, dry_run)
        finally:
            with _IN_PROGRESS_LOCK:
                _IN_PROGRESS.discard(src_key)

    def _organize_file_inner(self, src: Path, dry_run: bool) -> OrganizerResult:
        filepath = str(src)

        if not src.exists():
            return OrganizerResult(False, filepath, "", "error", "Source file not found")

        if not src.is_file():
            return OrganizerResult(False, filepath, "", "skipped", "Not a regular file")

        if src.name.startswith(".") or src.name.endswith(".tmp") or src.name.endswith("~"):
            return OrganizerResult(False, filepath, "", "skipped", "Temporary/hidden file ignored")

        # Safety: never touch files inside blacklisted system directories
        if _is_path_blacklisted(src.parent):
            logger.warning(f"[BLOCKED] '{src}' is inside a protected system folder — skipped.")
            return OrganizerResult(
                False, filepath, "", "skipped",
                f"Source is inside a protected system folder: {src.parent}"
            )

        category, dest_file = self.resolve_destination(filepath)
        if dest_file is None:
            return OrganizerResult(
                False, filepath, "", "skipped",
                f"No category matched extension '{src.suffix}' and unknown folder disabled",
            )

        dest_path = Path(dest_file)
        dest_dir  = dest_path.parent

        if dest_path.resolve() == src.resolve():
            return OrganizerResult(False, filepath, str(dest_path), "skipped",
                                   "File already in correct location")

        # Safety: never write into blacklisted system directories
        if _is_path_blacklisted(dest_dir):
            logger.warning(f"[BLOCKED] Destination '{dest_dir}' is a protected system folder — skipped.")
            return OrganizerResult(
                False, filepath, str(dest_path), "skipped",
                f"Destination is inside a protected system folder: {dest_dir}"
            )

        action = "moved"
        if dest_path.exists():
            resolved = self._handle_conflict(dest_path)
            if resolved is None:
                return OrganizerResult(
                    False, filepath, str(dest_path), "skipped",
                    "File already exists and conflict strategy is 'skip'",
                )
            if resolved != dest_path:
                action = "renamed"
            dest_path = resolved
            dest_dir  = dest_path.parent

        if dry_run:
            return OrganizerResult(True, filepath, str(dest_path), action,
                                   f"[DRY RUN] Would move to {category}")

        # ── actual move with retry ───────────────────────────────────────────
        # Create the destination directory ONLY now (all checks passed).
        dir_created = False
        try:
            if not dest_dir.exists():
                dest_dir.mkdir(parents=True, exist_ok=True)
                dir_created = True
        except OSError as e:
            logger.error(f"Cannot create destination dir '{dest_dir}': {e}")
            return OrganizerResult(False, filepath, str(dest_path), "error",
                                   f"Cannot create destination folder: {e}")

        # Retry up to 3 times — handles files briefly locked by antivirus /
        # Windows Explorer right after they land in the watched folder.
        last_error: Optional[Exception] = None
        for attempt in range(3):
            try:
                shutil.move(str(src), str(dest_path))
                logger.info(f"[{action.upper()}] '{src.name}' -> '{dest_path}'")
                last_error = None
                break
            except PermissionError as e:
                last_error = e
                if attempt < 2:
                    time.sleep(0.8)   # wait for file lock to release
            except OSError as e:
                last_error = e
                break   # non-permission OS errors are unlikely to clear up

        if last_error is not None:
            # Move failed — clean up the empty directory we just created so
            # the user doesn't see ghost folders.
            if dir_created:
                try:
                    dest_dir.rmdir()   # only removes if empty
                except OSError:
                    pass
            err_msg = str(last_error)
            logger.error(f"Failed to move '{src.name}': {err_msg}")
            return OrganizerResult(False, filepath, str(dest_path), "error", err_msg)

        return OrganizerResult(
            True, filepath, str(dest_path), action,
            f"Moved to {category}",
        )

    def organize_folder(self, folder: str, dry_run: bool = False) -> list:
        """
        Organize all files currently in a folder (non-recursive).
        Returns a list of OrganizerResult values.
        """
        results = []
        folder_path = Path(folder)
        if not folder_path.is_dir():
            logger.error(f"Folder not found: {folder}")
            return results

        # Refuse to touch blacklisted root folders entirely
        if _is_path_blacklisted(folder_path):
            logger.warning(f"[BLOCKED] Folder '{folder_path}' is a protected system folder — skipped entirely.")
            return results

        for item in folder_path.iterdir():
            if item.is_file():
                result = self.organize_file(str(item), dry_run=dry_run)
                results.append(result)

        return results
