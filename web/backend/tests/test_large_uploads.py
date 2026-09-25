"""Large uploads: 50 MB limit, and document info without re-reading big PDFs."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from pypdf import PdfWriter  # noqa: E402

import web.backend.document_stats as document_stats  # noqa: E402
import web.backend.main as main  # noqa: E402


def _pdf(path, pages=2):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as f:
        writer.write(f)


def test_upload_limit_is_50_mb():
    assert main.MAX_UPLOAD_BYTES == 50 * 1024 * 1024


def test_word_count_can_be_skipped(tmp_path, monkeypatch):
    pdf = tmp_path / "big.pdf"
    _pdf(pdf, pages=3)
    calls = []
    real_reader = document_stats.PdfReader

    class _CountingReader(real_reader):
        @property
        def pages(self):
            pages = super().pages
            calls.append(len(pages))
            return pages

    monkeypatch.setattr(document_stats, "PdfReader", _CountingReader)
    stats = document_stats.extract_document_stats(str(pdf), "big.pdf", count_words=False)
    assert stats["page_count"] == 3 and "word_count" not in stats
    assert calls == [3]  # pages were counted, but not iterated for text


def test_word_count_skipped_above_size_threshold(tmp_path, monkeypatch):
    pdf = tmp_path / "doc.pdf"
    _pdf(pdf)
    monkeypatch.setattr(document_stats, "WORD_COUNT_MAX_BYTES", 10)  # pretend the file is huge
    stats = document_stats.extract_document_stats(str(pdf), "doc.pdf")
    assert stats["page_count"] == 2 and "word_count" not in stats
