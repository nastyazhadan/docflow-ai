from __future__ import annotations

import html
import re
from typing import Iterable, List

from cleaner_service.models.dto import CleanItemIn, CleanItemOut

# Регулярки компилируются один раз при импорте модуля
_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    """
    Очищает текст:
    - декодирует HTML-сущности (&amp; -> &, &nbsp; -> пробел)
    - удаляет HTML-теги (<...>)
    - нормализует все виды whitespace до одного пробела
    - обрезает пробелы по краям

    Все операции выполняются за O(n) по длине строки.
    """
    if not text:
        return ""

    # 1) HTML entities (&amp;, &nbsp; и т.п.)
    text = html.unescape(text)

    # 2) Удаляем теги
    text = _TAG_RE.sub(" ", text)

    # 3) Нормализуем пробелы/переводы строк/табы
    text = _WHITESPACE_RE.sub(" ", text)

    # 4) Убираем пробелы по краям
    return text.strip()


class TextCleaner:
    """
    Сервис очистки текста.

    Stateless, не зависит от HTTP-слоя.
    """

    __slots__ = ()

    def clean(self, items: Iterable[CleanItemIn]) -> List[CleanItemOut]:
        """
        Принимает итерируемый набор CleanItemIn и возвращает список CleanItemOut.

        Алгоритмическая сложность: O(N), где N — суммарная длина content.
        """
        result: List[CleanItemOut] = []

        for item in items:
            raw = item.content or ""
            cleaned = _clean_text(raw)

            result.append(
                CleanItemOut(
                    source=item.source,
                    path=item.path,
                    url=item.url,
                    raw_content=raw,
                    cleaned_content=cleaned,
                )
            )

        return result
