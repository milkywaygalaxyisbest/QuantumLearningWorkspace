"""
Ingestion write side (source attribution audit): every stored chunk is tagged
with its own document, chunk ids never collide across documents, and a later
upload never overwrites an earlier one.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import embedding.chroma_store as chroma_store  # noqa: E402
from embedding.chunker import chunk_document  # noqa: E402

LR_TEXT = " ".join(f"regression{i} residual slope intercept" for i in range(600))
RAG_TEXT = " ".join(f"retrieval{i} augmented generation grounding" for i in range(600))


class _Vectors(list):
    def tolist(self):
        return list(self)


class _FakeModel:
    def encode(self, texts):
        return _Vectors([[0.0, 0.0] for _ in texts])


class _FakeCollection:
    def __init__(self):
        self.rows = {}

    def upsert(self, ids, embeddings, documents, metadatas):
        for i, chunk_id in enumerate(ids):
            self.rows[chunk_id] = (documents[i], metadatas[i])


def _store(monkeypatch, collection, text, document_id, title, user_id="a@x.com"):
    monkeypatch.setattr(chroma_store, "get_collection", lambda *a, **k: collection)
    monkeypatch.setattr(chroma_store, "get_embedding_model", lambda: _FakeModel())
    chunks = chunk_document({"source_type": "pdf", "title": title, "text": text, "metadata": {}})
    stored = chroma_store.store_chunks(chunks, user_id=user_id, document_id=document_id, title=title)
    return stored, chunks


def test_two_documents_are_stored_side_by_side_without_overwriting(monkeypatch):
    collection = _FakeCollection()
    n_lr, _ = _store(monkeypatch, collection, LR_TEXT, "doc-lr", "Linear Regression")
    n_rag, _ = _store(monkeypatch, collection, RAG_TEXT, "doc-rag", "RAG")
    assert n_lr > 1 and n_rag > 1
    assert len(collection.rows) == n_lr + n_rag  # nothing was overwritten


def test_every_chunk_is_tagged_with_its_own_document(monkeypatch):
    collection = _FakeCollection()
    _store(monkeypatch, collection, LR_TEXT, "doc-lr", "Linear Regression")
    _store(monkeypatch, collection, RAG_TEXT, "doc-rag", "RAG")
    titles = {"doc-lr": "Linear Regression", "doc-rag": "RAG"}
    words = {"doc-lr": "regression", "doc-rag": "retrieval"}
    for chunk_id, (text, meta) in collection.rows.items():
        assert chunk_id.startswith(f"{meta['document_id']}_")
        assert meta["document"] == titles[meta["document_id"]]
        assert meta["user_id"] == "a@x.com"
        assert words[meta["document_id"]] in text  # the text really belongs to that document


def test_chunk_indexes_are_unique_within_a_document(monkeypatch):
    collection = _FakeCollection()
    stored, chunks = _store(monkeypatch, collection, LR_TEXT, "doc-lr", "Linear Regression")
    indexes = [c["chunk_index"] for c in chunks]
    assert indexes == list(range(stored))
    assert len(collection.rows) == stored
