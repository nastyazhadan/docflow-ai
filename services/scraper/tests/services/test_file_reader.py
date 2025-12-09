from pathlib import Path

from scraper_service.services.file_reader import FileReader


def test_file_reader_reads_only_files(tmp_path: Path) -> None:
    # Arrange
    root = tmp_path / "root"
    root.mkdir()
    file1 = root / "a.txt"
    file2 = root / "b.md"
    subdir = root / "dir"
    subdir.mkdir()
    file3 = subdir / "c.txt"

    file1.write_text("hello", encoding="utf-8")
    file2.write_text("world", encoding="utf-8")
    file3.write_text("!", encoding="utf-8")

    reader = FileReader(root_dir=root, allowed_extensions=(".txt",))

    # Act
    files = list(reader.iter_files())

    # Assert
    paths = {f.path for f in files}
    contents = {f.content for f in files}

    assert paths == {"a.txt", "dir\\c.txt"}
    assert contents == {"hello", "!"}
