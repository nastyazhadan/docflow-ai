import pytest

from normalizer_service.models.dto import NormalizerItemIn
from normalizer_service.services.normalizer import TextNormalizer


@pytest.fixture()
def normalizer() -> TextNormalizer:
    return TextNormalizer()


def _make_item(text: str) -> NormalizerItemIn:
    return NormalizerItemIn(
        source="file",
        path="doc.txt",
        url=None,
        raw_content="ignored",
        cleaned_content=text,
    )


def test_normalizer_empty_text_skipped(normalizer: TextNormalizer) -> None:
    """
    Пустой cleaned_content не должен порождать чанков.
    """
    items = [
        _make_item(""),
        _make_item("   "),
        _make_item("\n\t"),
    ]

    result = normalizer.normalize(items)

    assert result == []


def test_normalizer_single_short_chunk(normalizer: TextNormalizer) -> None:
    """
    Текст короче лимита -> один чанк.
    """
    text = "This is a short text without splitting."
    items = [_make_item(text)]

    result = normalizer.normalize(items)

    assert len(result) == 1
    doc = result[0]

    assert doc.text == "This is a short text without splitting."
    assert doc.metadata.chunk_index == 0
    assert doc.metadata.total_chunks == 1
    assert doc.metadata.source == "file"
    assert doc.metadata.path == "doc.txt"
    assert doc.metadata.title == "doc.txt"
    assert doc.metadata.created_at.endswith("Z")


def test_normalizer_multiple_chunks_by_sentences() -> None:
    """
    Длинный текст с несколькими предложениями должен разбиться на несколько чанков.
    """
    normalizer = TextNormalizer(max_chunk_chars=50)

    text = (
        "Sentence one is quite long and maybe not enough. "
        "Sentence two is also here. "
        "Sentence three finishes the text."
    )
    items = [_make_item(text)]

    result = normalizer.normalize(items)

    # Проверяем, что чанков больше одного
    assert len(result) >= 2

    # Проверяем, что сумма длины чанков примерно равна длине текста (без учёта пробелов)
    total_len = sum(len(doc.text) for doc in result)
    assert total_len >= len(text) * 0.8  # грубая проверка на то, что ничего не потерялось

    # Проверяем индексацию чанков
    total_chunks = result[0].metadata.total_chunks
    assert total_chunks == len(result)
    indices = [doc.metadata.chunk_index for doc in result]
    assert indices == list(range(len(result)))


def test_normalizer_single_sentence_longer_than_limit() -> None:
    """
    Если одно "предложение" длиннее лимита, оно должно быть порезано по символам.
    """
    max_len = 50
    normalizer = TextNormalizer(max_chunk_chars=max_len)

    long_sentence = "x" * 120  # одно длинное "предложение"
    items = [_make_item(long_sentence)]

    result = normalizer.normalize(items)

    # 120 символов по 50 -> 3 чанка: 50, 50, 20
    assert len(result) == 3
    lengths = [len(doc.text) for doc in result]
    assert lengths[0] == max_len
    assert lengths[1] == max_len
    assert lengths[2] == 120 - 2 * max_len

    # Индексы должны быть 0,1,2
    indices = [doc.metadata.chunk_index for doc in result]
    assert indices == [0, 1, 2]

    # total_chunks во всех чанках одинаковое
    totals = {doc.metadata.total_chunks for doc in result}
    assert totals == {3}
