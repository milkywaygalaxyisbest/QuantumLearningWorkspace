"""Quiz generation scoped to one document."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import embedding.chroma_store as chroma_store  # noqa: E402
from quiz_generator.app.models.api_models import GenerateQuizRequest  # noqa: E402
from quiz_generator.app.services.quiz_service import QuizService  # noqa: E402


class _FakeCollection:
    def __init__(self):
        self.where = "not called"

    def query(self, query_embeddings, n_results, where=None):
        self.where = where
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}


class _FakeModel:
    def encode(self, text):
        return [[0.0, 0.0]]


def _where(monkeypatch, **kwargs):
    coll = _FakeCollection()
    monkeypatch.setattr(chroma_store, "get_collection", lambda *a, **k: coll)
    monkeypatch.setattr(chroma_store, "get_embedding_model", lambda: _FakeModel())
    chroma_store.query_chunks("linear regression", top_k=3, **kwargs)
    return coll.where


def test_query_chunks_combines_user_and_document_with_and(monkeypatch):
    assert _where(monkeypatch, user_id="a@x.com", document_id="vec-lr") == {
        "$and": [{"user_id": "a@x.com"}, {"document_id": "vec-lr"}]
    }


def test_query_chunks_single_condition_unchanged(monkeypatch):
    assert _where(monkeypatch, user_id="a@x.com") == {"user_id": "a@x.com"}
    assert _where(monkeypatch) is None


def test_request_accepts_optional_document_id():
    assert GenerateQuizRequest(topic="t", quiz_type="mcq").document_id is None
    assert GenerateQuizRequest(topic="t", quiz_type="mcq", document_id="vec-lr").document_id == "vec-lr"


def test_quiz_service_passes_document_id_to_search():
    seen = {}

    class _FakeEmbedder:
        def search(self, query, top_k=5, user_id=None, document_id=None):
            seen.update(user_id=user_id, document_id=document_id)
            return []

    service = QuizService.__new__(QuizService)
    service.embedder = _FakeEmbedder()
    result = service.generate_quiz_from_topic(
        topic="linear regression", question_type="mcq", user_id="a@x.com", document_id="vec-lr"
    )
    assert seen == {"user_id": "a@x.com", "document_id": "vec-lr"}
    assert "error" in result
