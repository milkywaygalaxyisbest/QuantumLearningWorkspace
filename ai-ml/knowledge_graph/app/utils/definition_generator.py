"""
Generates a short, one-sentence definition/summary for a document,
used to populate the knowledge graph's node detail view. Uses Groq —
same provider already used by relationship_classifier.py — so no new
API dependency.

Falls back to an empty string on any failure (missing key, network
error, malformed response) rather than raising, so a definition
problem never breaks graph building or ingestion.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# Load .env directly rather than relying on some other module having
# already loaded it first — makes this file safe to import and use
# standalone, not just as part of the full ingestion pipeline.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent.parent / ".env")

DEFAULT_DEFINITION = ""

_PROMPT_TEMPLATE = """Write ONE short sentence (max 25 words) defining what this study document is about, suitable for a student browsing a knowledge graph. Do not include the document's title in your answer. Respond with ONLY the sentence, no preamble.

Document text:
{text}

Definition:"""

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        _client = Groq(api_key=api_key)
    return _client


def generate_definition(text: str, model: str = "openai/gpt-oss-20b") -> str:
    """
    Returns a short definition string, or DEFAULT_DEFINITION ("") on
    any failure. Never raises.
    """
    if not text or not text.strip():
        return DEFAULT_DEFINITION

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": _PROMPT_TEMPLATE.format(text=text[:1500]),
            }],
            temperature=0.3,
            max_tokens=300,
            reasoning_effort="low",
        )
        definition = response.choices[0].message.content.strip()
        return definition or DEFAULT_DEFINITION

    except Exception:
        return DEFAULT_DEFINITION