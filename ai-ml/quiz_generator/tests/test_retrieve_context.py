"""/retrieve-context returns the user's most relevant chunks for flashcards."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import quiz_generator.app.main as main  # noqa: E402
from quiz_generator.app.models.api_models import RetrieveContextRequest  # noqa: E402


class _FakeEmbedder:
    def __init__(self):
        self.calls = []

    def search(self, query, top_k=5, user_id=None, document_id=None):
        self.calls.append((query, top_k, user_id, document_id))
        return [
            {"text": "OLS minimises squared residuals.", "title": "lr.pdf", "score": 0.3, "metadata": {}},
            {"text": "", "title": "lr.pdf", "score": 0.9, "metadata": {}},
        ]


class _FakeService:
    def __init__(self):
        self.embedder = _FakeEmbedder()


def test_retrieve_context_is_scoped_and_skips_empty_chunks(monkeypatch):
    service = _FakeService()
    monkeypatch.setattr(main, "get_service", lambda: service)
    body = RetrieveContextRequest(query="Core Concepts", top_k=4, document_id="vec-lr")
    result = main.retrieve_context_endpoint(body, user_id="a@x.com")
    assert service.embedder.calls == [("Core Concepts", 4, "a@x.com", "vec-lr")]
    assert result.success is True
    assert [c["text"] for c in result.chunks] == ["OLS minimises squared residuals."]


def test_request_defaults():
    body = RetrieveContextRequest(query="x")
    assert body.top_k == 6 and body.document_id is None
