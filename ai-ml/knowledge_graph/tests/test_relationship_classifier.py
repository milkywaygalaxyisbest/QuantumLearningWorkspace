"""
Tests for relationship_classifier.py. All Groq API calls are mocked —
these test the module's own logic (fallback safety, label parsing),
not the LLM itself.

Run: pytest knowledge_graph/tests/test_relationship_classifier.py
"""
from unittest.mock import patch, MagicMock

import pytest

import knowledge_graph.app.utils.relationship_classifier as rc


@pytest.fixture(autouse=True)
def reset_client():
    """Ensures the singleton Groq client doesn't leak between tests."""
    rc._client = None
    yield
    rc._client = None


def test_missing_api_key_falls_back_safely(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    result = rc.classify_relationship("text A", "text B")
    assert result == rc.DEFAULT_RELATIONSHIP_TYPE


def test_valid_classification_returned(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("knowledge_graph.app.utils.relationship_classifier.Groq") as MockGroq:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "prerequisite_of"
        MockGroq.return_value.chat.completions.create.return_value = mock_response

        result = rc.classify_relationship("Intro to ML", "Decision Trees")
        assert result == "prerequisite_of"


def test_messy_output_still_parses_correctly(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("knowledge_graph.app.utils.relationship_classifier.Groq") as MockGroq:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "  Prerequisite_Of!!! (probably)"
        MockGroq.return_value.chat.completions.create.return_value = mock_response

        result = rc.classify_relationship("A", "B")
        assert result == "prerequisite_of"


def test_unrecognized_output_falls_back(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("knowledge_graph.app.utils.relationship_classifier.Groq") as MockGroq:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "banana"
        MockGroq.return_value.chat.completions.create.return_value = mock_response

        result = rc.classify_relationship("A", "B")
        assert result == rc.DEFAULT_RELATIONSHIP_TYPE


def test_api_failure_falls_back_without_crashing(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("knowledge_graph.app.utils.relationship_classifier.Groq") as MockGroq:
        MockGroq.return_value.chat.completions.create.side_effect = Exception("network error")

        result = rc.classify_relationship("A", "B")
        assert result == rc.DEFAULT_RELATIONSHIP_TYPE


@pytest.mark.parametrize("label", ["prerequisite_of", "example_of", "contrasts_with", "related_to"])
def test_all_valid_types_recognized(monkeypatch, label):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    with patch("knowledge_graph.app.utils.relationship_classifier.Groq") as MockGroq:
        mock_response = MagicMock()
        mock_response.choices[0].message.content = label
        MockGroq.return_value.chat.completions.create.return_value = mock_response

        result = rc.classify_relationship("A", "B")
        assert result == label
