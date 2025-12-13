from __future__ import annotations

import html
import re
from typing import Iterable, List

from cleaner_service.models.dto import CleanItemIn, CleanItemOut

# 1) Удаляем целиком <style>...</style> и <script>...</script>
_STYLE_SCRIPT_BLOCK_RE = re.compile(r"(?is)<(style|script)\b[^>]*>.*?</\1>")

# 2) Комментарии HTML (иногда много мусора)
_HTML_COMMENT_RE = re.compile(r"(?s)<!--.*?-->")

# 3) Любые теги
_TAG_RE = re.compile(r"(?s)<[^>]+>")

# Строгий матч одного "токена" селектора:
# - tag (body)
# - .class
# - #id
# - псевдоклассы/псевдоэлементы (a:link)
# - атрибуты ([href^='https'])
_SELECTOR_RE = r"(?:[#.])?[_a-zA-Z][\w\-]*(?:[#.:][\w\-]+|\[[^\]]+\])*"

# Важно: НЕ используем \b, иначе .class/#id не матчится целиком.
# Вместо этого: "слева не буква/цифра/подчёркивание/дефис" — чтобы не съедать куски слов.
_CSS_BLOCK_RE = re.compile(
    rf"(?is)(?<![\w-]){_SELECTOR_RE}(?:\s*,\s*{_SELECTOR_RE})*\s*\{{[^}}]*:[^}}]*\}}"
)

_WHITESPACE_RE = re.compile(r"\s+")


def _clean_text(text: str) -> str:
    """
    Очищает текст:
    - декодирует HTML-сущности
    - вырезает <style>/<script> блоки целиком
    - удаляет HTML-комментарии
    - удаляет HTML-теги
    - удаляет оставшиеся CSS-блоки selector{...}
    - нормализует пробелы
    """
    if not text:
        return ""

    # 1) HTML entities (&amp;, &nbsp; и т.п.)
    text = html.unescape(text)

    # 2) Убираем целиком style/script (чтобы CSS/JS не превращался в "текст")
    text = _STYLE_SCRIPT_BLOCK_RE.sub(" ", text)

    # 3) Убираем HTML-комментарии
    text = _HTML_COMMENT_RE.sub(" ", text)

    # 4) Удаляем теги
    text = _TAG_RE.sub(" ", text)

    # 5) Убираем “CSS-правила”, если они просочились (body{...}h1{...} и т.д.)
    # делаем несколько проходов, чтобы подряд идущие блоки удалились корректно
    for _ in range(3):
        new_text = _CSS_BLOCK_RE.sub(" ", text)
        if new_text == text:
            break
        text = new_text

    # 6) Нормализуем пробелы/переводы строк/табы
    text = _WHITESPACE_RE.sub(" ", text)

    return text.strip()


class TextCleaner:
    __slots__ = ()

    def clean(self, items: Iterable[CleanItemIn]) -> List[CleanItemOut]:
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
