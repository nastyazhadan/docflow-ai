from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

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

    def iter_files(self, pattern: Optional[str] = None) -> Iterable[FileContent]:
        """Ленивый обход файлов.

        - если pattern указан — используем glob(pattern)
        - иначе — полный обход rglob("*")
        """
        if pattern:
            candidates = self._root_dir.glob(pattern)
        else:
            candidates = self._root_dir.rglob("*")

        for path in candidates:
            if not self._is_allowed(path):
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            yield FileContent(
                path=str(path.relative_to(self._root_dir)),
                content=text,
            )

    def read_all(self, pattern: Optional[str] = None) -> list[FileContent]:
        # Собираем в список, когда нужно отдать JSON
        return list(self.iter_files(pattern))
