from pathlib import Path

from scraper_service.services.file_reader import FileReader


def test_read_all_empty_dir(tmp_path: Path):
    reader = FileReader(root_dir=tmp_path)
    files = reader.read_all()
    assert files == []


def test_read_all_single_file(tmp_path: Path):
    f = tmp_path / "doc1.txt"
    f.write_text("hello", encoding="utf-8")

    reader = FileReader(root_dir=tmp_path)
    files = reader.read_all()

    assert len(files) == 1
    item = files[0]
    assert item.path == "doc1.txt"
    assert item.content == "hello"


def test_read_all_with_pattern(tmp_path: Path):
    (tmp_path / "keep.md").write_text("md", encoding="utf-8")
    (tmp_path / "skip.txt").write_text("txt", encoding="utf-8")

    reader = FileReader(root_dir=tmp_path)
    files = reader.read_all(pattern="**/*.md")

    assert len(files) == 1
    assert files[0].path.endswith("keep.md")
