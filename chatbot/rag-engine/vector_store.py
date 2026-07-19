"""Embed chunks with SentenceTransformer and store/query them in ChromaDB."""

from __future__ import annotations

from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_COLLECTION_NAME = "study_chunks"


def load_embedding_model(model_name: str = DEFAULT_MODEL_NAME) -> SentenceTransformer:
    """Load the local embedding model used for documents and queries."""
    return SentenceTransformer(model_name)


def create_collection(name: str = DEFAULT_COLLECTION_NAME):
    """Create an in-memory Chroma collection (ephemeral for demo scripts)."""
    client = chromadb.Client()
    return client.create_collection(name=name)


def add_chunks(collection, embedding_model: SentenceTransformer, chunks: list[dict]) -> None:
    """Embed each chunk and add it to the collection with metadata."""
    if not chunks:
        return

    ids = [chunk["id"] for chunk in chunks]
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [chunk["metadata"] for chunk in chunks]
    embeddings = embedding_model.encode(documents).tolist()

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )


def retrieve(
    collection,
    embedding_model: SentenceTransformer,
    question: str,
    n_results: int = 1,
) -> dict[str, Any]:
    """
    Query the collection for the top-n chunks matching the question.

    Returns a dict with:
      - documents: list[str]
      - distances: list[float] | None
      - metadatas: list[dict] | None
      - ids: list[str] | None
    """
    question_embedding = embedding_model.encode(question).tolist()
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=n_results,
    )

    return {
        "documents": results["documents"][0] if results.get("documents") else [],
        "distances": results["distances"][0] if results.get("distances") else None,
        "metadatas": results["metadatas"][0] if results.get("metadatas") else None,
        "ids": results["ids"][0] if results.get("ids") else None,
    }


def format_retrieved_chunks(documents: list[str]) -> str:
    """Join one or more retrieved chunks for the LLM prompt."""
    if not documents:
        return ""
    if len(documents) == 1:
        return documents[0]
    parts = []
    for i, doc in enumerate(documents, start=1):
        parts.append(f"[Chunk {i}]\n{doc}")
    return "\n\n".join(parts)
