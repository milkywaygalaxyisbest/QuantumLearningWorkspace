"""Split long documents into ~200-300 word chunks for embedding."""

from pathlib import Path


TARGET_MIN_WORDS = 200
TARGET_MAX_WORDS = 300


def load_text(path: str | Path) -> str:
    """Load a UTF-8 text file and normalize line endings."""
    return Path(path).read_text(encoding="utf-8").strip()


def _word_count(text: str) -> int:
    return len(text.split())


def _split_oversized(paragraph: str, max_words: int = TARGET_MAX_WORDS) -> list[str]:
    """Split a single oversized paragraph into word windows of max_words."""
    words = paragraph.split()
    if len(words) <= max_words:
        return [paragraph.strip()] if paragraph.strip() else []

    pieces = []
    for start in range(0, len(words), max_words):
        piece = " ".join(words[start : start + max_words]).strip()
        if piece:
            pieces.append(piece)
    return pieces


def chunk_text(
    text: str,
    source: str = "",
    min_words: int = TARGET_MIN_WORDS,
    max_words: int = TARGET_MAX_WORDS,
) -> list[dict]:
    """
    Chunk text by blank-line paragraphs, merging short ones and splitting long ones
    so each chunk lands roughly between min_words and max_words.
    """
    raw_paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    # Flatten any oversized paragraphs into word windows first
    paragraphs: list[str] = []
    for para in raw_paragraphs:
        paragraphs.extend(_split_oversized(para, max_words=max_words))

    merged: list[str] = []
    buffer = ""

    for para in paragraphs:
        candidate = f"{buffer}\n\n{para}".strip() if buffer else para
        if buffer and _word_count(candidate) > max_words:
            merged.append(buffer)
            buffer = para
        else:
            buffer = candidate
            # Flush early if we are already in the target band and next merge would overshoot
            if _word_count(buffer) >= min_words:
                # Keep growing until max_words unless this para alone already hit max
                if _word_count(buffer) >= max_words:
                    merged.append(buffer)
                    buffer = ""

    if buffer:
        # Fold short leftovers into the previous chunk when possible
        if merged and _word_count(buffer) < min_words:
            combined = f"{merged[-1]}\n\n{buffer}".strip()
            if _word_count(combined) <= max_words + (min_words // 2):
                merged[-1] = combined
            else:
                merged.append(buffer)
        else:
            merged.append(buffer)

    chunks = []
    for index, chunk_body in enumerate(merged):
        chunks.append(
            {
                "id": f"chunk_{index}",
                "text": chunk_body,
                "metadata": {
                    "source": source,
                    "chunk_index": index,
                    "word_count": _word_count(chunk_body),
                },
            }
        )
    return chunks


def chunk_file(path: str | Path, min_words: int = TARGET_MIN_WORDS, max_words: int = TARGET_MAX_WORDS) -> list[dict]:
    """Load a file and return chunk dicts with source metadata."""
    file_path = Path(path)
    text = load_text(file_path)
    return chunk_text(text, source=file_path.name, min_words=min_words, max_words=max_words)
