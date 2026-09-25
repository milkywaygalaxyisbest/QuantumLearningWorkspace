"""
Which chat messages count as real questions on the profile page.

A message counts when it contains at least one word (2+ letters or digits)
that is not a greeting, thanks, acknowledgement or other casual filler.
So "Hi", "Hello!", "ok thanks" and "good morning" are not counted, while
"What is linear regression?", "explain photosynthesis", "AI?" and "why?" are.

The same word list is used by web/frontend/src/components/questionFilter.js;
keep the two in sync.
"""
from __future__ import annotations

import re
from typing import Any

CASUAL_WORDS = frozenset({
    "accha", "acha", "achha", "afternoon", "ah", "alaikum", "alot", "alright",
    "aoa", "are", "assalam", "assalamualaikum", "awesome", "bro", "buddy", "bye",
    "care", "cool", "cya", "day", "dear", "doing", "evening", "fine",
    "friend", "gm", "good", "goodbye", "got", "great", "greetings", "haan",
    "haha", "han", "hehe", "hello", "helo", "hey", "heya", "heyy",
    "hi", "hii", "hiii", "hiya", "hm", "hmm", "how", "it",
    "jazakallah", "ji", "k", "kk", "later", "lol", "lot", "maam",
    "madam", "mam", "meherbani", "morning", "much", "nah", "nice", "night",
    "no", "nope", "noted", "oh", "ok", "okay", "okey", "okk",
    "perfect", "please", "pls", "plz", "salaam", "salam", "see", "shukria",
    "shukriya", "sir", "sis", "so", "sup", "sure", "take", "thank",
    "thanks", "thanku", "thankyou", "theek", "there", "thik", "thx", "ty",
    "tysm", "u", "uh", "um", "understood", "up", "very", "wa",
    "walaikum", "welcome", "whats", "wow", "yea", "yeah", "yep", "yes",
    "yo", "you", "yup",
})

# Letters/digits in any script (so Urdu or Arabic text counts too); apostrophes
# are removed first so "what's" reads as "whats".
_WORD_RE = re.compile(r"[^\W_]+")


def is_meaningful_question(text: Any) -> bool:
    """True if the message is a real question rather than casual chat."""
    if not isinstance(text, str):
        return False
    normalized = text.lower().replace("'", "").replace("\u2019", "")
    return any(
        len(word) >= 2 and word not in CASUAL_WORDS
        for word in _WORD_RE.findall(normalized)
    )


async def count_meaningful_questions(chat_history, user_id: str) -> int:
    """Count this user's saved chat messages that are meaningful questions.

    Computed from the stored history on every call, so older casual messages
    are excluded too; no one-time data correction is needed.
    """
    count = 0
    async for doc in chat_history.find({"user_id": user_id, "role": "user"}):
        if is_meaningful_question(doc.get("content")):
            count += 1
    return count
