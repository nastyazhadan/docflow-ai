from pathlib import Path
from typing import Iterable

from scraper_service.models.dto import FileContent


class FileReader:
    """Отвечает за чтение файлов из директории.

    Алгоритм:
    - одно проходное сканирование дерева каталогов (O(N) по числу файлов)
    - ленивое чтение через генератор
    """

    def __init__(
            self,
            root_dir: Path,
            allowed_extensions: tuple[str, ...] | None = None,
    ) -> None:
        self._root_dir = root_dir
        self._allowed_extensions = allowed_extensions

    def _is_allowed(self, path: Path) -> bool:
        if not path.is_file():
            return False
        if self._allowed_extensions is None:
            return True
        return path.suffix.lower() in self._allowed_extensions

    def iter_files(self) -> Iterable[FileContent]:
        # Один проход по дереву, без лишних аллокаций коллекций
        for path in self._root_dir.rglob("*"):
            if not self._is_allowed(path):
                continue
            # Читаем файл полностью – иначе JSON всё равно не собрать
            text = path.read_text(encoding="utf-8", errors="ignore")
            yield FileContent(path=str(path.relative_to(self._root_dir)), content=text)

    def read_all(self) -> list[FileContent]:
        # Если нужно собрать в список (для JSON)
        return list(self.iter_files())
