"""Profile question count: casual messages are not counted as questions."""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from web.backend.question_counter import (  # noqa: E402
    count_meaningful_questions,
    is_meaningful_question,
)

CASUAL = [
    "Hi", "hello!", "Hey there", "ok thanks", "Thank you so much!",
    "good morning", "bye", "what's up", "Assalam o alaikum", "shukriya",
    "   ", "?", "k", None,
]
REAL = [
    "What is linear regression?", "explain photosynthesis", "photosynthesis",
    "AI?", "why?", "hi, what is gradient descent?",
    "thanks! can you summarize chapter 2", "linear regression kya hai",
]


@pytest.mark.parametrize("text", CASUAL)
def test_casual_messages_are_not_questions(text):
    assert is_meaningful_question(text) is False


@pytest.mark.parametrize("text", REAL)
def test_real_questions_are_counted(text):
    assert is_meaningful_question(text) is True


class _FakeCursor:
    def __init__(self, docs):
        self._docs = iter(docs)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._docs)
        except StopIteration:
            raise StopAsyncIteration


class _FakeCollection:
    def __init__(self, docs):
        self.docs = docs

    def find(self, query):
        return _FakeCursor(
            d for d in self.docs if all(d.get(k) == v for k, v in query.items())
        )


def test_count_only_this_users_meaningful_questions():
    docs = [
        {"user_id": "a@x.com", "role": "user", "content": "Hi"},
        {"user_id": "a@x.com", "role": "assistant", "content": "Hello! How can I help?"},
        {"user_id": "a@x.com", "role": "user", "content": "What is linear regression?"},
        {"user_id": "a@x.com", "role": "user", "content": "thanks"},
        {"user_id": "a@x.com", "role": "user", "content": "explain RAG", "document_id": "d1"},
        {"user_id": "b@x.com", "role": "user", "content": "What is RAG?"},
    ]
    assert asyncio.run(count_meaningful_questions(_FakeCollection(docs), "a@x.com")) == 2
