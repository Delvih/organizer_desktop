"""
Core file organization logic.
"""

import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from .config import Config


logger = logging.getLogger("FileOrganizer")


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
        Uses a manually configured destination root when present; otherwise
        falls back to system folders for common media types.
        """
        if self.config.destination_folder:
            return Path(self.config.destination_folder) / category

        system_folders = {
            "Documents": Path.home() / "Documents",
            "Images": Path.home() / "Pictures",
            "Videos": Path.home() / "Videos",
            "Music": Path.home() / "Music",
        }
        system_root = system_folders.get(category)
        if system_root is not None:
            return system_root

        return Path.home() / "Documents" / "FileOrganizer" / category

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
        """
        src = Path(filepath)

        if not src.exists():
            return OrganizerResult(False, filepath, "", "error", "Source file not found")

        if not src.is_file():
            return OrganizerResult(False, filepath, "", "skipped", "Not a regular file")

        if src.name.startswith(".") or src.name.endswith(".tmp") or src.name.endswith("~"):
            return OrganizerResult(False, filepath, "", "skipped", "Temporary/hidden file ignored")

        category, dest_file = self.resolve_destination(filepath)
        if dest_file is None:
            return OrganizerResult(
                False,
                filepath,
                "",
                "skipped",
                f"No category matched extension '{src.suffix}' and unknown folder disabled",
            )

        dest_path = Path(dest_file)
        dest_dir = dest_path.parent

        if dest_path.resolve() == src.resolve():
            return OrganizerResult(False, filepath, str(dest_path), "skipped", "File already in correct location")

        action = "moved"
        if dest_path.exists():
            resolved = self._handle_conflict(dest_path)
            if resolved is None:
                return OrganizerResult(
                    False,
                    filepath,
                    str(dest_path),
                    "skipped",
                    "File already exists and conflict strategy is 'skip'",
                )
            if resolved != dest_path:
                action = "renamed"
            dest_path = resolved
            dest_dir = dest_path.parent

        if not dry_run:
            try:
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src), str(dest_path))
                logger.info(f"[{action.upper()}] '{src.name}' -> '{dest_path}'")
            except PermissionError as e:
                logger.error(f"Permission denied moving '{src.name}': {e}")
                return OrganizerResult(False, filepath, str(dest_path), "error", f"Permission denied: {e}")
            except OSError as e:
                logger.error(f"OS error moving '{src.name}': {e}")
                return OrganizerResult(False, filepath, str(dest_path), "error", str(e))

        return OrganizerResult(
            True,
            filepath,
            str(dest_path),
            action,
            f"Moved to {category} via wrapper folder",
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

        for item in folder_path.iterdir():
            if item.is_file():
                result = self.organize_file(str(item), dry_run=dry_run)
                results.append(result)

        return results
