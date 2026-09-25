from __future__ import annotations
from typing import Optional

from pydantic import BaseModel, Field


class GenerateQuizRequest(BaseModel):
    """
    Request body for POST /generate-quiz.

    No user_id field here — per Contract v1 Section 2, identity is
    never trusted from client input. The authenticated user_id comes
    from the verified JWT (see auth.py's get_current_user_id).
    """

    topic: str = Field(..., min_length=1, description="Topic to generate the quiz from.")
    question_count: int = Field(
        default=5, ge=1, le=20, description="Number of questions to generate."
    )
    quiz_type: str = Field(
        ...,
        description="One of: mcq, true_false, fill_blank, short_answer.",
    )
    document_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description=(
            "Optional: limit retrieval to one of the user's documents "
            "(chunk metadata document_id, i.e. the upload's vector_document_id)."
        ),
    )


class GenerateQuizResponse(BaseModel):
    """
    Response body for POST /generate-quiz.

    Per Contract v1 Section 10, the existing question/answer split
    stays: "questions" never includes correct answers; "answers" is
    a separate list matched by question_id for the caller (Pluto) to
    store and grade against. This matches docs/api-contracts.md.
    """

    success: bool
    message: str
    questions: list[dict] = Field(default_factory=list)
    answers: list[dict] = Field(default_factory=list)


class RetrieveContextRequest(BaseModel):
    """Request body for POST /retrieve-context (used by flashcard generation)."""

    query: str = Field(..., min_length=1, max_length=500, description="Topic to retrieve study material for.")
    top_k: int = Field(default=6, ge=1, le=12, description="Number of chunks to return.")
    document_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Optional: only search this document (chunk metadata document_id).",
    )


class RetrieveContextResponse(BaseModel):
    success: bool
    chunks: list[dict] = Field(default_factory=list)
