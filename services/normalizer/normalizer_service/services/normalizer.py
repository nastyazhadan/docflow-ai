from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List
from urllib.parse import urlparse

from normalizer_service.models.dto import (
    Metadata,
    NormalizerItemIn,
    NormalizedDocument,
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_whitespace(text: str) -> str:
    """
    Схлопывает все виды whitespace до одного пробела и обрезает края.
    O(n) по длине строки.
    """
    if not text:
        return ""
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _split_into_sentences(text: str) -> List[str]:
    """
    Наивное разбиение на "предложения" по . ! ?
    O(n) по длине строки.
    """
    text = text.strip()
    if not text:
        return []

    parts = _SENTENCE_SPLIT_RE.split(text)
    sentences: List[str] = []
    for part in parts:
        part = part.strip()
        if part:
            sentences.append(part)
    return sentences or [text]


@dataclass(frozen=True)
class _ChunkingConfig:
    max_chunk_chars: int = 1000  # можно подправить при инициализации сервиса


class TextNormalizer:
    """
    Сервис нормализации: принимает документы после cleaner, возвращает
    список чанков с метаданными.

    Stateless, O(N) по суммарной длине текста.
    """

    __slots__ = ("_config",)

    def __init__(self, max_chunk_chars: int = 1000) -> None:
        if max_chunk_chars <= 0:
            raise ValueError("max_chunk_chars must be positive")
        self._config = _ChunkingConfig(max_chunk_chars=max_chunk_chars)

    def _build_chunks(self, text: str) -> List[str]:
        """
        Разбивает текст на чанки не длиннее max_chunk_chars.
        - сначала делим на предложения
        - собираем чанки из предложений
        - если одно "предложение" длиннее лимита, режем его по символам

        Все операции O(n).
        """
        text = _normalize_whitespace(text)
        if not text:
            return []

        sentences = _split_into_sentences(text)
        chunks: List[str] = []
        current_parts: List[str] = []
        current_len = 0
        max_len = self._config.max_chunk_chars

        for sentence in sentences:
            if not sentence:
                continue

            sent_len = len(sentence)

            # Если само "предложение" больше лимита — режем его по частям
            if sent_len > max_len:
                if current_parts:
                    chunks.append(" ".join(current_parts))
                    current_parts = []
                    current_len = 0

                start = 0
                while start < sent_len:
                    end = min(start + max_len, sent_len)
                    part = sentence[start:end]
                    chunks.append(part)
                    start = end
                continue

            # Обычный случай: пробуем добавить предложение в текущий чанк
            # +1 за пробел между предложениями, если чанк не пустой
            extra = 1 if current_parts else 0
            if current_len + extra + sent_len <= max_len:
                current_parts.append(sentence)
                current_len += extra + sent_len
            else:
                # Чанк заполнен, начинаем новый
                if current_parts:
                    chunks.append(" ".join(current_parts))
                current_parts = [sentence]
                current_len = sent_len

        if current_parts:
            chunks.append(" ".join(current_parts))

        return chunks

    @staticmethod
    def _derive_title(item: NormalizerItemIn) -> str:
        """
        Эвристика заголовка:

        - если есть path -> берём имя файла из него
        - если path нет, но есть url -> берём последний сегмент пути,
          а если он пустой — целиком URL
        - иначе возвращаем "document"
        """
        # 1) Файлы: имя файла из path
        if item.path:
            name = Path(item.path).name
            if name:
                return name

        # 2) HTTP: пробуем вытащить что-то из URL
        if item.url:
            url_str = str(item.url)
            parsed = urlparse(url_str)

            # путь без хвостового слэша, берем последний сегмент
            path = parsed.path.rstrip("/") or "/"
            last_segment = path.split("/")[-1]

            if last_segment:
                return last_segment
            return url_str  # fallback — весь URL

        # 3) Полный fallback
        return "document"

    def normalize(self, items: Iterable[NormalizerItemIn]) -> List[NormalizedDocument]:
        """
        Главный метод: из входных items (после cleaner) делает список чанков.
        O(N) по суммарной длине cleaned_content.
        """
        normalized: List[NormalizedDocument] = []

        for item in items:
            text = item.cleaned_content or ""
            chunks = self._build_chunks(text)

            if not chunks:
                # Пустой текст — просто пропускаем, не создаём пустых документов
                continue

            # created_at для всех чанков из одного документа одинаковый
            created_at = (
                datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )

            total = len(chunks)
            title = self._derive_title(item)

            for idx, chunk_text in enumerate(chunks):
                external_id = f"{item.source}:{item.path}:{idx}"

                # path должен быть строкой:
                # - для файлов берём item.path
                # - для HTTP подставляем url (или пустую строку как последний fallback)
                if item.path is not None:
                    meta_path = item.path
                elif item.url is not None:
                    meta_path = str(item.url)
                else:
                    meta_path = ""

                metadata = Metadata(
                    source=item.source,
                    path=meta_path,
                    url=item.url,
                    title=title,
                    created_at=created_at,
                    chunk_index=idx,
                    total_chunks=total,
                )

                normalized.append(
                    NormalizedDocument(
                        external_id=external_id,
                        text=chunk_text,
                        metadata=metadata,
                    )
                )

        return normalized
