"""Document scoping shared by the chat and quiz proxies."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from bson import ObjectId  # noqa: E402

import web.backend.document_scope as document_scope  # noqa: E402

MONGO_ID = ObjectId()
RECORDS = [
    {"_id": MONGO_ID, "user_id": "a@x.com", "document_id": "web-lr",
     "vector_document_id": "vec-lr", "filename": "Linear Regression.pdf", "upload_date": "2026-01-01"},
    {"_id": ObjectId(), "user_id": "a@x.com", "document_id": "web-rag",
     "vector_document_id": "vec-rag", "filename": "RAG.pdf", "upload_date": "2026-01-02"},
    {"_id": ObjectId(), "user_id": "b@x.com", "document_id": "web-b",
     "vector_document_id": "vec-b", "filename": "RAG.pdf"},
]


class _FakeUploads:
    async def find_one(self, query, sort=None):
        rows = [r for r in RECORDS if r["user_id"] == query["user_id"]]
        if "$or" in query:
            for r in rows:
                for cond in query["$or"]:
                    (key, value), = cond.items()
                    if r.get(key) == value:
                        return r
            return None
        rows = [r for r in rows if r.get("filename") == query.get("filename")]
        if sort:
            rows.sort(key=lambda r: r.get("upload_date", ""), reverse=True)
        return rows[0] if rows else None


def _resolve(monkeypatch, *args):
    monkeypatch.setattr(document_scope, "get_uploads_collection", lambda: _FakeUploads())
    return asyncio.run(document_scope.resolve_vector_document_id(*args))


def test_upload_document_id_maps_to_vector_id(monkeypatch):
    assert _resolve(monkeypatch, "a@x.com", "web-lr", None) == ("vec-lr", "Linear Regression.pdf")


def test_vector_id_and_mongo_id_are_accepted(monkeypatch):
    assert _resolve(monkeypatch, "a@x.com", "vec-rag", None)[0] == "vec-rag"
    assert _resolve(monkeypatch, "a@x.com", str(MONGO_ID), None)[0] == "vec-lr"


def test_filename_only(monkeypatch):
    assert _resolve(monkeypatch, "a@x.com", None, "RAG.pdf") == ("vec-rag", "RAG.pdf")


def test_other_users_id_is_not_translated(monkeypatch):
    assert _resolve(monkeypatch, "a@x.com", "web-b", None) == ("web-b", None)


def test_nothing_selected(monkeypatch):
    assert _resolve(monkeypatch, "a@x.com", None, None) == (None, None)
