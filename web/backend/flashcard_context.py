"""
Study material for flashcard generation, retrieved from the user's own documents.

Flashcards used to be generated from the topic name alone (or from the first part
of a PDF that may no longer be on disk), which produced generic questions. This
asks the ai-ml retrieval endpoint (same vector search the quiz generator uses)
for the chunks most relevant to the topic, optionally limited to one document.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from web.backend.auth_utils import create_access_token
from web.backend.document_scope import resolve_vector_document_id

logger = logging.getLogger("uvicorn")

QUIZ_SERVICE_URL = os.getenv("QUIZ_SERVICE_URL", "http://localhost:8002")
DEFAULT_TOP_K = 6


async def retrieve_flashcard_context(
    user_email: str,
    topic: str,
    document_id: Optional[str] = None,
    top_k: int = DEFAULT_TOP_K,
) -> Optional[str]:
    """
    Returns the retrieved chunk texts joined into one reference block, or None
    if nothing could be retrieved (service unreachable, no matching content).
    """
    body = {"query": topic, "top_k": top_k}
    if document_id:
        # Chunks are tagged with the upload's vector_document_id, not the id the UI sends.
        scope_id, _ = await resolve_vector_document_id(user_email, document_id, None)
        if scope_id:
            body["document_id"] = scope_id

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=5.0)) as client:
            response = await client.post(
                f"{QUIZ_SERVICE_URL.rstrip('/')}/retrieve-context",
                json=body,
                headers={"Authorization": f"Bearer {create_access_token(user_email)}"},
            )
        if response.status_code != 200:
            logger.warning(f"Flashcard context retrieval returned {response.status_code}: {response.text[:200]}")
            return None
        chunks = response.json().get("chunks") or []
    except Exception as e:
        logger.warning(f"Flashcard context retrieval failed: {e}")
        return None

    texts, seen = [], set()
    for chunk in chunks:
        text = (chunk.get("text") or "").strip()
        if text and text not in seen:
            seen.add(text)
            texts.append(text)
    return "\n\n---\n\n".join(texts) or None
