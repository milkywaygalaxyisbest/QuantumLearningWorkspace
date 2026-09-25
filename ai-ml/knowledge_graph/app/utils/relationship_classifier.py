"""
Classifies the semantic relationship between two pieces of text using
an LLM (Groq — same provider already used by definition_generator.py
and the chatbot elsewhere in this project, so no new API dependency).

Falls back to "related_to" (the existing default) on any failure —
missing API key, network error, malformed response, or an
unrecognized label — so a classification problem degrades gracefully
instead of breaking graph building entirely.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# Load .env directly rather than relying on some other module having
# already loaded it first — makes this file safe to import and use
# standalone, not just as part of the full ingestion pipeline.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")

# The fixed set of relationship types the graph understands. Keeping
# this closed (rather than letting the LLM invent arbitrary labels)
# makes the field predictable for the frontend to filter/display on.
VALID_RELATIONSHIP_TYPES = {
    "prerequisite_of",
    "example_of",
    "contrasts_with",
    "related_to",  # fallback / general case
}

DEFAULT_RELATIONSHIP_TYPE = "related_to"

_PROMPT_TEMPLATE = """You are classifying the relationship between two pieces of study content. Respond with EXACTLY ONE of these labels, nothing else:

prerequisite_of - text A should be understood before text B
example_of - text B is a specific example illustrating a concept from text A
contrasts_with - text A and text B present differing or opposing ideas
related_to - they share a topic but none of the above apply clearly

Text A:
{text_a}

Text B:
{text_b}

Label:"""

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        _client = Groq(api_key=api_key)
    return _client


def classify_relationship(text_a: str, text_b: str, model: str = "openai/gpt-oss-20b") -> str:
    """
    Returns one of VALID_RELATIONSHIP_TYPES. Never raises — any
    failure (missing key, network error, unexpected model output)
    falls back to DEFAULT_RELATIONSHIP_TYPE, so a classification
    issue never breaks graph building.

    [Fix] gpt-oss-20b is a reasoning model — Groq bills its hidden
    internal reasoning against max_tokens. At default reasoning
    effort, short-answer prompts can exhaust the whole token budget
    on reasoning and return empty content (finish_reason: "length").
    reasoning_effort="low" keeps enough budget free for the actual
    one-word answer. (This surfaced first in definition_generator.py,
    which produces longer output and hit the failure reliably; this
    classifier likely had the same latent risk with shorter answers.)
    """
    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": _PROMPT_TEMPLATE.format(text_a=text_a[:500], text_b=text_b[:500]),
            }],
            temperature=0,
            max_tokens=100,
            reasoning_effort="low",
        )
        raw_label = response.choices[0].message.content.strip().lower()

        for label in VALID_RELATIONSHIP_TYPES:
            if label in raw_label:
                return label

        return DEFAULT_RELATIONSHIP_TYPE

    except Exception:
        return DEFAULT_RELATIONSHIP_TYPE