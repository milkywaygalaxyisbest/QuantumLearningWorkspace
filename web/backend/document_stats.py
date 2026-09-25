"""
Size, page count and word count of an uploaded document.

Computed once while the file is still on disk (during processing) and saved on
the upload record, so the document info view keeps working after the file is
gone, e.g. after a redeploy or restart wipes the upload directory.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

from pypdf import PdfReader


# Counting words means extracting the text of every page with pypdf, which is
# slow for big PDFs; above this size the word count is left to the ingestion
# service, which already extracts the text (see process_file_ingestion).
WORD_COUNT_MAX_BYTES = 15 * 1024 * 1024


def extract_document_stats(
    file_path: Optional[str], filename: str = "", count_words: bool = True
) -> Dict[str, Any]:
    """
    Returns only the values that could be determined:
    {"file_size_bytes": int, "page_count": int, "word_count": int}.
    Missing file -> {}. Non-PDF -> size only. PDF with no extractable text
    (e.g. scanned) -> no word_count.
    """
    stats: Dict[str, Any] = {}
    if not file_path or not os.path.exists(file_path):
        return stats
    stats["file_size_bytes"] = os.path.getsize(file_path)
    if file_path.lower().endswith(".pdf") or (filename or "").lower().endswith(".pdf"):
        try:
            reader = PdfReader(file_path)
            stats["page_count"] = len(reader.pages)
            if count_words and stats["file_size_bytes"] <= WORD_COUNT_MAX_BYTES:
                text = "".join((page.extract_text() or "") for page in reader.pages)
                if text.strip():
                    stats["word_count"] = len(text.split())
        except Exception:
            pass
    return stats


def format_file_size(size_bytes: Optional[int]) -> Optional[str]:
    """Same format the preview endpoint always returned, e.g. "1.25 MB"."""
    if size_bytes is None:
        return None
    return f"{size_bytes / (1024 * 1024):.2f} MB"
