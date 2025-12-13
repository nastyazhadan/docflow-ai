import pytest
from fastapi.testclient import TestClient

from cleaner_service.main import cleaner_app
from cleaner_service.models.dto import CleanItemIn
from cleaner_service.services.cleaner import TextCleaner


@pytest.fixture()
def cleaner() -> TextCleaner:
    return TextCleaner()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Пустые значения (границы)
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

        # Скрипты / стили должны удаляться полностью (ключевое)
        ("<script>alert('x')</script>Hi", "Hi"),
        ("<style>body{color:red}</style>Hi", "Hi"),

        # CSS-блоки, которые могут “просочиться” как текст
        # Важно: не должны съедать соседние слова
        ("Example body{background:#eee} Domain", "Example Domain"),

        # Вложенные теги
        ("<div><span>Inner</span> text</div>", "Inner text"),

        # Комбо
        ("  <p>Hi,&nbsp;&nbsp;world!</p>\n", "Hi, world!"),

        # --- Доп. кейсы по CSS (примерно как на example.com) ---

        # Псевдоклассы и запятые (a:link,a:visited{...})
        ("Hello a:link,a:visited{color:#348} world", "Hello world"),

        # Несколько CSS-правил подряд
        (
                "A body{background:#eee} B h1{font-size:1.5em} C div{opacity:0.8} D",
                "A B C D",
        ),

        # CSS с классами/айди
        ("Start .btn-primary{color:#fff} End", "Start End"),
        ("Start #header{height:10px} End", "Start End"),

        # CSS с атрибутами (редко, но встречается)
        ("X a[href^='https']{text-decoration:none} Y", "X Y"),

        # Убедимся, что { } без ":" не удаляются как CSS (чтобы не терять полезный текст)
        ("Keep {this} text", "Keep {this} text"),
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

    assert out.source == "file"
    assert out.path == "doc.txt"
    assert out.url is None

    assert out.raw_content == raw
    assert out.cleaned_content == expected


def test_cleaner_empty_items_list(cleaner: TextCleaner) -> None:
    result = cleaner.clean([])
    assert result == []


def test_cleaner_multiple_items(cleaner: TextCleaner) -> None:
    items = [
        CleanItemIn(source="file", path="a.txt", url=None, content="<p>A</p>"),
        CleanItemIn(source="http", path=None, url="https://example.com", content="B"),
    ]

    result = cleaner.clean(items)

    assert len(result) == 2
    first, second = result

    assert first.source == "file"
    assert first.path == "a.txt"
    assert first.url is None
    assert first.raw_content == "<p>A</p>"
    assert first.cleaned_content == "A"

    assert second.source == "http"
    assert second.path is None
    assert second.url == "https://example.com"
    assert second.raw_content == "B"
    assert second.cleaned_content == "B"


def test_cleaner_removes_css_blocks_without_eating_neighbor_words(cleaner: TextCleaner) -> None:
    """
    Защита от регресса: CSS-удалялка не должна съедать слова рядом с CSS.
    """
    raw = "Example body{background:#eee} Domain"
    item = CleanItemIn(source="http", path=None, url="https://example.com", content=raw)

    out = cleaner.clean([item])[0].cleaned_content

    assert out == "Example Domain"
    assert "body{" not in out.lower()


def test_cleaner_removes_style_tag_content_completely(cleaner: TextCleaner) -> None:
    """
    <style>...</style> должен исчезать полностью, включая содержимое.
    """
    raw = "<style>body{background:#eee}</style><h1>Title</h1>"
    item = CleanItemIn(source="http", path=None, url="https://example.com", content=raw)

    out = cleaner.clean([item])[0].cleaned_content.lower()

    assert "title" in out
    assert "body{" not in out
    assert "background" not in out


client = TestClient(cleaner_app)


def test_clean_returns_context():
    resp = client.post(
        "/clean",
        json={
            "context": {"space_id": "space-1"},
            "items": [
                {"source": "file", "path": "doc.txt", "url": None, "content": "<p>Hello</p>"}
            ],
        },
    )

    assert resp.status_code == 200
    body = resp.json()

    assert body["context"]["space_id"] == "space-1"
    assert len(body["items"]) == 1
    assert body["items"][0]["cleaned_content"] == "Hello"
