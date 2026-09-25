"""Document info (size / pages / words) is computed once and can be stored."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from pypdf import PdfWriter  # noqa: E402

from web.backend.document_stats import extract_document_stats, format_file_size  # noqa: E402


def _blank_pdf(path, pages):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as f:
        writer.write(f)


def test_pdf_pages_and_size(tmp_path):
    pdf = tmp_path / "notes.pdf"
    _blank_pdf(pdf, 3)
    stats = extract_document_stats(str(pdf), "notes.pdf")
    assert stats["page_count"] == 3
    assert stats["file_size_bytes"] == os.path.getsize(pdf)
    assert "word_count" not in stats  # blank pages have no text


def test_missing_file_returns_nothing():
    assert extract_document_stats(None) == {}
    assert extract_document_stats("does/not/exist.pdf", "exist.pdf") == {}


def test_non_pdf_gets_size_only(tmp_path):
    txt = tmp_path / "a.txt"
    txt.write_text("hello world")
    assert extract_document_stats(str(txt), "a.txt") == {"file_size_bytes": 11}


def test_format_file_size():
    assert format_file_size(None) is None
    assert format_file_size(1024 * 1024) == "1.00 MB"
