from __future__ import annotations

import base64

import pytest

from scraper_service.models.dto import UploadedFilePayload
from scraper_service.services.uploaded_file_decoder import UploadedFileDecoder


def _b64(s: str) -> str:
    return base64.b64encode(s.encode("utf-8")).decode("ascii")


def test_decode_empty_input():
    dec = UploadedFileDecoder()
    out = dec.decode_to_file_contents([])
    assert out == []


def test_decode_single_file_ok():
    dec = UploadedFileDecoder()
    files = [
        UploadedFilePayload(
            name="doc1.txt",
            content_b64=_b64("hello"),
            encoding="base64",
        )
    ]

    out = dec.decode_to_file_contents(files)

    assert len(out) == 1
    item = out[0]
    assert item.path == "doc1.txt"
    assert item.content == "hello"


def test_decode_multiple_files_ok():
    dec = UploadedFileDecoder()
    files = [
        UploadedFilePayload(name="a.txt", content_b64=_b64("AAA"), encoding="base64"),
        UploadedFilePayload(name="b.txt", content_b64=_b64("BBB"), encoding="base64"),
    ]

    out = dec.decode_to_file_contents(files)

    assert [x.path for x in out] == ["a.txt", "b.txt"]
    assert [x.content for x in out] == ["AAA", "BBB"]


def test_decode_invalid_base64_raises():
    dec = UploadedFileDecoder()
    files = [
        UploadedFilePayload(
            name="bad.txt",
            content_b64="!!!notbase64!!!",
            encoding="base64",
        )
    ]

    with pytest.raises(ValueError, match="Invalid base64 in content_b64"):
        dec.decode_to_file_contents(files)


def test_decode_per_file_size_limit_raises():
    # raw "AAAA" = 4 bytes, ставим лимит 3
    dec = UploadedFileDecoder(max_file_bytes=3)
    files = [
        UploadedFilePayload(
            name="big.txt",
            content_b64=base64.b64encode(b"AAAA").decode("ascii"),
            encoding="base64",
        )
    ]

    with pytest.raises(ValueError, match=r"File too large: big\.txt"):
        dec.decode_to_file_contents(files)


def test_decode_total_size_limit_raises():
    # 2 файла по 4 байта => суммарно 8, ставим лимит 7
    dec = UploadedFileDecoder(max_total_bytes=7)

    files = [
        UploadedFilePayload(name="a.bin", content_b64=base64.b64encode(b"AAAA").decode("ascii"), encoding="base64"),
        UploadedFilePayload(name="b.bin", content_b64=base64.b64encode(b"BBBB").decode("ascii"), encoding="base64"),
    ]

    with pytest.raises(ValueError, match=r"Total upload too large: 8 bytes"):
        dec.decode_to_file_contents(files)


def test_decode_uses_text_encoding_and_replaces_invalid_bytes():
    # bytes: b'\xff' is invalid in utf-8; should become replacement char "�"
    dec = UploadedFileDecoder(text_encoding="utf-8")
    files = [
        UploadedFilePayload(
            name="x.bin",
            content_b64=base64.b64encode(b"\xff").decode("ascii"),
            encoding="base64",
        )
    ]

    out = dec.decode_to_file_contents(files)
    assert len(out) == 1
    assert out[0].path == "x.bin"
    assert out[0].content == "�"
