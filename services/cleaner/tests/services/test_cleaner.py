import pytest

from cleaner_service.models.dto import CleanItemIn
from cleaner_service.services.cleaner import TextCleaner


@pytest.fixture()
def cleaner() -> TextCleaner:
    """Фикстура для TextCleaner, используется во всех тестах."""
    return TextCleaner()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Пустые значения
        ("", ""),
        ("   ", ""),
        ("\n\t\r", ""),

        # Уже нормальный текст
        ("Plain text", "Plain text"),

        # Простые HTML-теги
        ("<p>Hello</p>", "Hello"),
        ("<div>Hello   world</div>", "Hello world"),

        # HTML-сущности
        ("Hello&nbsp;world", "Hello world"),
        ("Rock &amp; Roll", "Rock & Roll"),

        # Многострочный текст с табами
        ("Line1\n\nLine2\t\tLine3", "Line1 Line2 Line3"),

        # Скрипты и вложенные теги
        ("<script>alert('x')</script>Hi", "alert('x') Hi"),
        ("<div><span>Inner</span> text</div>", "Inner text"),

        # Комбо
        ("  <p>Hi,&nbsp;&nbsp;world!</p>\n", "Hi, world!"),
    ],
)
def test_cleaner_content_normalization(cleaner: TextCleaner, raw: str, expected: str) -> None:
    item = CleanItemIn(
        source="file",
        path="doc.txt",
        url=None,
        content=raw,
    )

    result = cleaner.clean([item])

    assert len(result) == 1
    out = result[0]

    # Поля пробрасываются как есть
    assert out.source == "file"
    assert out.path == "doc.txt"
    assert out.url is None

    # Контент обрабатывается корректно
    assert out.raw_content == raw
    assert out.cleaned_content == expected


def test_cleaner_empty_items_list(cleaner: TextCleaner) -> None:
    """
    Пограничный случай: пустой список items.
    """
    result = cleaner.clean([])

    assert result == []


def test_cleaner_multiple_items(cleaner: TextCleaner) -> None:
    """
    Проверяем, что несколько элементов обрабатываются независимо и линейно.
    """
    items = [
        CleanItemIn(source="file", path="a.txt", url=None, content="<p>A</p>"),
        CleanItemIn(source="file", path="b.txt", url="https://example.com", content="B"),
    ]

    result = cleaner.clean(items)

    assert len(result) == 2

    first, second = result

    assert first.path == "a.txt"
    assert first.url is None
    assert first.raw_content == "<p>A</p>"
    assert first.cleaned_content == "A"

    assert second.path == "b.txt"
    assert second.url == "https://example.com"
    assert second.raw_content == "B"
    assert second.cleaned_content == "B"
