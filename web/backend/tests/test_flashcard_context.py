"""Flashcards are generated from retrieved document content, not the topic label."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import web.backend.flashcard_context as flashcard_context  # noqa: E402
import web.backend.routes.flashcards as flashcards  # noqa: E402
from web.backend.models import Flashcard, GenerateFlashcardsRequest  # noqa: E402


class _FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def _fake_client(calls, status_code=200, payload=None):
    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None, headers=None):
            calls.append({"url": url, "json": json})
            return _FakeResponse(status_code, payload or {})

    return _Client


def test_retrieval_scopes_to_vector_document_and_joins_chunks(monkeypatch):
    calls = []

    async def fake_resolve(user, doc_id, filename):
        return "vec-lr", None

    monkeypatch.setattr(flashcard_context, "resolve_vector_document_id", fake_resolve)
    monkeypatch.setattr(flashcard_context.httpx, "AsyncClient", _fake_client(calls, payload={
        "chunks": [{"text": "OLS minimises squared residuals."}, {"text": "OLS minimises squared residuals."},
                   {"text": "The slope is cov(x, y) / var(x)."}]
    }))
    text = asyncio.run(flashcard_context.retrieve_flashcard_context("a@x.com", "Core Concepts", "web-lr"))
    assert calls[0]["url"].endswith("/retrieve-context")
    assert calls[0]["json"] == {"query": "Core Concepts", "top_k": 6, "document_id": "vec-lr"}
    assert text == "OLS minimises squared residuals.\n\n---\n\nThe slope is cov(x, y) / var(x)."


def test_retrieval_failure_returns_none(monkeypatch):
    monkeypatch.setattr(flashcard_context.httpx, "AsyncClient", _fake_client([], status_code=502))
    assert asyncio.run(flashcard_context.retrieve_flashcard_context("a@x.com", "Topic")) is None


def _run_generate(monkeypatch, request, retrieved):
    seen = {}

    async def fake_retrieve(user, topic, document_id=None):
        seen["retrieve"] = (user, topic, document_id)
        return retrieved

    async def fake_groq(topic, count=5, difficulty="medium", content=None):
        seen["content"] = content
        return [Flashcard(id=str(i), front=f"Q{i}", back=f"A{i}", question=f"Q{i}", answer=f"A{i}",
                          topic=topic, difficulty=difficulty) for i in range(count)]

    monkeypatch.setattr(flashcards, "retrieve_flashcard_context", fake_retrieve)
    monkeypatch.setattr(flashcards, "_generate_groq_flashcards", fake_groq)
    monkeypatch.setattr(flashcards, "_extract_document_text", lambda doc_id: "PDF: fallback text")
    result = asyncio.run(flashcards.generate_flashcards(request, current_user_email="A@x.com "))
    return result, seen


def test_document_content_goes_to_the_llm_even_with_colons(monkeypatch):
    chunks = "Residual: observed minus predicted value.\n\nR-squared: share of variance explained."
    request = GenerateFlashcardsRequest(topic="Core Concepts", num_cards=3, document_id="web-lr")
    result, seen = _run_generate(monkeypatch, request, chunks)
    assert seen["retrieve"] == ("a@x.com", "Core Concepts", "web-lr")
    assert seen["content"] == chunks  # not diverted to the "Term: Definition" template path
    assert [c.front for c in result.cards] == ["Q0", "Q1", "Q2"]


def test_pdf_text_is_only_a_fallback(monkeypatch):
    request = GenerateFlashcardsRequest(topic="Core Concepts", num_cards=2, document_id="web-lr")
    _, seen = _run_generate(monkeypatch, request, None)
    assert seen["content"] == "PDF: fallback text"


def test_user_notes_still_use_term_definition_extraction(monkeypatch):
    notes = "Mean: average value\nMedian: middle value\nMode: most frequent value"
    request = GenerateFlashcardsRequest(topic="Statistics", num_cards=3, content=notes)
    result, seen = _run_generate(monkeypatch, request, "should not be used")
    assert "retrieve" not in seen and "content" not in seen
    assert len(result.cards) == 3 and "Mean" in result.cards[0].front
