from __future__ import annotations

import os
import logging
from typing import Optional, List, Dict, Any
import httpx
from dotenv import load_dotenv

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from web.backend.auth_utils import get_current_user_email, create_access_token
from web.backend.document_scope import resolve_vector_document_id

load_dotenv()

logger = logging.getLogger("uvicorn")
router = APIRouter()

CHATBOT_SERVICE_URL = os.getenv("CHATBOT_SERVICE_URL", "http://localhost:8000")


class HistoryItem(BaseModel):
    role: str
    content: str


class AskRequest(BaseModel):
    question: str
    history: Optional[List[HistoryItem]] = None
    filename: Optional[str] = None
    document_id: Optional[str] = None
    top_k: Optional[int] = 5
    include_sources: Optional[bool] = True
    rerank: Optional[bool] = True
    multi_hop: Optional[bool] = False
    skip_cache: Optional[bool] = False


# ---------------- Proxy Endpoint ----------------

@router.post("/ask")
async def ask(
    request: AskRequest,
    req: Request,
    current_user_email: str = Depends(get_current_user_email),
):
    # Strictly derive user_id from the authenticated JWT session (email) only.
    resolved_user_id = current_user_email.strip().lower()

    # Selected document -> id stored on its chunks, so the chatbot searches only that document.
    scope_document_id, scope_filename = await resolve_vector_document_id(
        resolved_user_id, request.document_id, request.filename
    )

    # Helper to check if user is asking for a general summary/overview
    q_lower = request.question.lower().strip()
    summary_phrases = [
        "tell me about this document", "tell me about this", "summarize",
        "overview", "what is this document about", "explain this document",
        "what does this document say", "summary"
    ]

    outgoing_question = request.question
    if any(p in q_lower for p in summary_phrases):
        if scope_filename:
            outgoing_question = f"Provide a detailed summary and overview of the main topics, sections, and key details in the document '{scope_filename}'."
        else:
            outgoing_question = "Provide a detailed summary and overview of the main topics, sections, and key details in the uploaded study documents."

    # Build payload for chatbot service
    payload: Dict[str, Any] = {
        "question": outgoing_question,
        "user_id": resolved_user_id,
        "history": [
            {
                "role": h.role,
                "content": h.content,
            }
            for h in (request.history or [])
        ],
        "top_k": request.top_k,
        "include_sources": request.include_sources,
        "rerank": request.rerank,
        "multi_hop": request.multi_hop,
        "skip_cache": request.skip_cache,
    }

    if scope_filename:
        payload["filename"] = scope_filename
    if scope_document_id:
        payload["document_id"] = scope_document_id

    target_url = f"{CHATBOT_SERVICE_URL.rstrip('/')}/ask"

    # Forward the Bearer authorization header to chatbot service
    forward_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {create_access_token(resolved_user_id)}",
    }

    try:
        timeout = httpx.Timeout(
            connect=10.0,
            read=90.0,
            write=10.0,
            pool=10.0,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                target_url,
                json=payload,
                headers=forward_headers,
            )

        if response.status_code == 200:
            res_json = response.json()
            # If user sent a simple greeting, do not attach unrelated document sources
            greetings = {"hi", "hello", "hey", "good morning", "good evening", "thanks", "thank you", "hi!", "hello!"}
            if request.question.lower().strip() in greetings:
                res_json["sources"] = []
                res_json["timing"] = None
            return res_json

        error_detail = response.text
        try:
            err_json = response.json()
            if isinstance(err_json, dict) and "detail" in err_json:
                error_detail = err_json["detail"]
        except Exception:
            pass

        raise HTTPException(
            status_code=response.status_code,
            detail=error_detail,
        )

    except HTTPException:
        raise

    except httpx.ReadTimeout as e:
        logger.warning(f"Chatbot connection timeout: {e}")
        raise HTTPException(
            status_code=504,
            detail="Chatbot took too long to respond. Please try again.",
        )

    except httpx.ConnectError as e:
        logger.warning(f"Chatbot connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "Chatbot service is unavailable. "
                f"Please make sure the chatbot server is running on {CHATBOT_SERVICE_URL}."
            ),
        )

    except Exception as e:
        logger.error(f"Chatbot unexpected error: {e}")
        raise HTTPException(
            status_code=503,
            detail=(
                "Chatbot service is currently unavailable. "
                "Please make sure it's running and try again."
            ),
        )


@router.delete("/chat/document/{document_id}")
@router.delete("/internal/cache/document/{document_id}")
async def delete_document_chat_cache(
    document_id: str,
    current_user_email: str = Depends(get_current_user_email),
):
    """Proxy endpoint to call Team Mu's cache invalidation endpoint for a specific document."""
    resolved_user_id = current_user_email.strip().lower()
    clean_doc_id = document_id.strip()
    target_url = f"{CHATBOT_SERVICE_URL.rstrip('/')}/internal/cache/document/{clean_doc_id}"
    forward_headers = {
        "Authorization": f"Bearer {create_access_token(resolved_user_id)}",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            res = await client.delete(target_url, headers=forward_headers)
            try:
                data = res.json()
            except Exception:
                data = {"status_code": res.status_code, "text": res.text}
            return {"success": res.status_code == 200, "data": data}
    except Exception as e:
        logger.warning(f"Failed to call Team Mu cache invalidation: {e}")
        return {"success": False, "error": str(e)}

