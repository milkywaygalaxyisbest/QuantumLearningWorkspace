"""
Team Lambda Quiz API — FastAPI service.

Run from ai-ml/ (so the quiz_generator.* and embedding.* imports resolve):
  uvicorn quiz_generator.app.main:app --reload --port 8002

Interactive docs: http://127.0.0.1:8002/docs
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from embedding.chroma_store import delete_chunks

from quiz_generator.app.models.api_models import (
    GenerateQuizRequest,
    GenerateQuizResponse,
    RetrieveContextRequest,
    RetrieveContextResponse,
)
from quiz_generator.app.services.quiz_service import QuizService
from quiz_generator.app.auth import get_current_user_id

app = FastAPI(title="StudyMind Quiz API — Team Lambda")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_service: QuizService | None = None


def get_service() -> QuizService:
    global _service
    if _service is None:
        _service = QuizService()
    return _service


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/retrieve-context", response_model=RetrieveContextResponse)
def retrieve_context_endpoint(
    body: RetrieveContextRequest,
    user_id: str = Depends(get_current_user_id),
) -> RetrieveContextResponse:
    """
    The user's stored chunks most relevant to `query`, optionally limited to one
    document. Same user-scoped vector search that quiz generation uses; the web
    backend calls this to build flashcards from real document content.
    """
    try:
        results = get_service().embedder.search(
            body.query, top_k=body.top_k, user_id=user_id, document_id=body.document_id
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Retrieval failed: {exc}") from exc
    chunks = [
        {"text": r.get("text", ""), "title": r.get("title", ""), "score": r.get("score")}
        for r in (results or [])
        if (r.get("text") or "").strip()
    ]
    return RetrieveContextResponse(success=True, chunks=chunks)


@app.post("/generate-quiz", response_model=GenerateQuizResponse)
def generate_quiz_endpoint(
    body: GenerateQuizRequest,
    user_id: str = Depends(get_current_user_id),
) -> GenerateQuizResponse:
    """
    [Contract v1, Section 10] Requires "Authorization: Bearer <jwt>".
    user_id is derived from the verified token (never from client
    input) and used to scope retrieval to this user's own content only.
    """
    service = get_service()

    valid_types = {"mcq", "true_false", "fill_blank", "short_answer"}
    if body.quiz_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"quiz_type must be one of: {', '.join(sorted(valid_types))}",
        )

    try:
        result = service.generate_quiz_from_topic(
            topic=body.topic,
            question_type=body.quiz_type,
            user_id=user_id,
            number_of_questions=body.question_count,
            document_id=body.document_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if "error" in result:
        return GenerateQuizResponse(
            success=False,
            message=result["error"],
            questions=[],
            answers=[],
        )

    return GenerateQuizResponse(
        success=True,
        message=f"Generated {len(result['questions'])} questions.",
        questions=result["questions"],
        answers=result["answers"],
    )

@app.delete("/document/{document_id}")
def delete_document_endpoint(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
) -> dict:
    """
    [P0-5] Purge all chunks for a document from the shared ChromaDB
    store. Idempotent — calling this on an already-deleted or
    nonexistent document_id is a safe no-op, not an error.

    Requires a valid JWT (Contract v1 Section 4/10) — but note the
    authenticated user_id is not currently cross-checked against the
    document's own user_id metadata before deleting. That ownership
    check should happen wherever documents/uploads are tracked
    (Pluto's side) before calling this endpoint.
    """
    delete_chunks(document_id)
    return {"success": True, "message": f"Document {document_id} purged."}