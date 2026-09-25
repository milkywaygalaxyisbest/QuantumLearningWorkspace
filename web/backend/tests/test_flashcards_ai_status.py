"""/flashcards/ai-status reports whether AI generation is configured, without secrets."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

import web.backend.routes.flashcards as flashcards  # noqa: E402


def test_status_without_key_records_the_reason(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    cards = asyncio.run(flashcards._generate_groq_flashcards("Topic", 3, "medium", "some material"))
    assert cards == []
    status = asyncio.run(flashcards.flashcards_ai_status(current_user_email="a@x.com"))
    assert status["groq_api_key_set"] is False
    assert "GROQ_API_KEY" in status["last_ai_error"]


def test_status_never_returns_the_key_value(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_secret_value")
    status = asyncio.run(flashcards.flashcards_ai_status(current_user_email="a@x.com"))
    assert status["groq_api_key_set"] is True
    assert "gsk_secret_value" not in str(status)


def test_groq_error_is_recorded(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_x")

    class _Completions:
        async def create(self, **kwargs):
            raise RuntimeError("model_not_found: openai/gpt-oss-120b")

    class _Client:
        def __init__(self, *args, **kwargs):
            self.chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr(flashcards, "AsyncGroq", _Client)
    assert asyncio.run(flashcards._generate_groq_flashcards("Topic", 3, "medium", "material")) == []
    status = asyncio.run(flashcards.flashcards_ai_status(current_user_email="a@x.com"))
    assert "model_not_found" in status["last_ai_error"]
