from pathlib import Path
from app.organizer import FileOrganizer


class DummyConfig:
    def __init__(self, dest_root: str):
        self.destination_folder = dest_root
        self.conflict_strategy = "rename"
        self.unknown_enabled = True
        self.unknown_folder = "Misc"

    def get_extension_map(self):
        return {".pdf": "Documents"}


def test_organize_file_moves(tmp_path):
    dest = tmp_path / "dest"
    cfg = DummyConfig(str(dest))

    src_dir = tmp_path / "src"
    src_dir.mkdir()
    src_file = src_dir / "sample.pdf"
    src_file.write_text("data")

    organizer = FileOrganizer(cfg)
    result = organizer.organize_file(str(src_file))
    assert result.success is True

    out_path = dest / "Documents" / "sample.pdf"
    assert out_path.exists()
