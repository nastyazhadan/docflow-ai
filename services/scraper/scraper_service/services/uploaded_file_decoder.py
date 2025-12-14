from __future__ import annotations

import base64
from typing import Iterable

from scraper_service.models.dto import FileContent, UploadedFilePayload


class UploadedFileDecoder:
    __slots__ = ("_max_file_bytes", "_max_total_bytes", "_text_encoding")

    def __init__(
            self,
            *,
            max_file_bytes: int = 5 * 1024 * 1024,
            max_total_bytes: int = 15 * 1024 * 1024,
            text_encoding: str = "utf-8",
    ) -> None:
        self._max_file_bytes = max_file_bytes
        self._max_total_bytes = max_total_bytes
        self._text_encoding = text_encoding

    def decode_to_file_contents(self, files: Iterable[UploadedFilePayload]) -> list[FileContent]:
        out: list[FileContent] = []
        total = 0

        for f in files:
            raw = self._b64decode_strict(f.content_b64)
            size = len(raw)

            if size > self._max_file_bytes:
                raise ValueError(f"File too large: {f.name} ({size} bytes)")

            total += size
            if total > self._max_total_bytes:
                raise ValueError(f"Total upload too large: {total} bytes")

            text = raw.decode(self._text_encoding, errors="replace")
            out.append(FileContent(path=f.name, content=text))

        return out

    @staticmethod
    def _b64decode_strict(data_b64: str) -> bytes:
        try:
            return base64.b64decode(data_b64, validate=True)
        except Exception as e:
            raise ValueError("Invalid base64 in content_b64") from e
