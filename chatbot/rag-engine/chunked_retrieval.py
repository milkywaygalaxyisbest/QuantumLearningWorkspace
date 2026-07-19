"""
Part A demo: chunk a real document, embed into ChromaDB, retrieve, and call Groq.

Usage:
  python chunked_retrieval.py
  python chunked_retrieval.py --k 2
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from chunker import chunk_file
from vector_store import (
    add_chunks,
    create_collection,
    format_retrieved_chunks,
    load_embedding_model,
    retrieve,
)

DATA_FILE = Path(__file__).resolve().parent / "data" / "photosynthesis_overview.txt"
DEFAULT_QUESTION = "Where do the light-dependent reactions take place?"
COMBINE_QUESTION = (
    "Compare the light-dependent reactions and the Calvin cycle: "
    "where each happens and what each produces."
)


def build_messages(retrieved_text: str, question: str) -> list[dict]:
    return [
        {
            "role": "system",
            "content": (
                "Answer the user's question using ONLY the provided reference chunk(s). "
                "If the chunk(s) do not contain the answer, say so."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Reference chunk(s):\n{retrieved_text}\n\nQuestion: {question}"
            ),
        },
    ]


def run(question: str, n_results: int) -> None:
    # Prefer local .env, then chatbot/, then repo root
    load_dotenv(DATA_FILE.parent.parent.parent / ".env")
    load_dotenv(DATA_FILE.parent.parent / ".env")
    load_dotenv()

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Source document not found: {DATA_FILE}")

    print(f"Loading document: {DATA_FILE.name}")
    chunks = chunk_file(DATA_FILE)
    print(f"Created {len(chunks)} chunk(s):\n")
    for chunk in chunks:
        preview = " ".join(chunk["text"].split()[:18])
        meta = chunk["metadata"]
        print(
            f"  [{chunk['id']}] words={meta['word_count']} "
            f"preview={preview}..."
        )

    print("\nLoading embedding model...")
    embedding_model = load_embedding_model()
    collection = create_collection(name="study_chunks")

    print("Embedding chunks and storing in ChromaDB...")
    add_chunks(collection, embedding_model, chunks)

    print(f"\nQuestion: {question}")
    print(f"Retrieving top-{n_results} chunk(s)...")
    results = retrieve(collection, embedding_model, question, n_results=n_results)

    documents = results["documents"]
    if not documents:
        print("No chunks retrieved.")
        return

    for i, doc in enumerate(documents):
        distance = None
        if results["distances"] is not None:
            distance = results["distances"][i]
        chunk_id = results["ids"][i] if results["ids"] else f"result_{i}"
        dist_label = f", distance={distance:.4f}" if distance is not None else ""
        print(f"\n--- Retrieved {chunk_id}{dist_label} ---")
        print(doc[:500] + ("..." if len(doc) > 500 else ""))

    retrieved_text = format_retrieved_chunks(documents)

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("\nGROQ_API_KEY not set; skipping LLM call.")
        return

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=build_messages(retrieved_text, question),
        temperature=0.3,
    )

    print("\nLLM Final Answer:\n")
    print(response.choices[0].message.content)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Chunked RAG retrieval demo")
    parser.add_argument(
        "--k",
        type=int,
        default=1,
        help="Number of chunks to retrieve (default: 1; use 2 for stretch goal)",
    )
    parser.add_argument(
        "--question",
        type=str,
        default=None,
        help="Override the default test question",
    )
    parser.add_argument(
        "--combine",
        action="store_true",
        help="Ask a multi-section compare question (pairs well with --k 2)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.combine:
        question = args.question or COMBINE_QUESTION
    else:
        question = args.question or DEFAULT_QUESTION
    run(question=question, n_results=max(1, args.k))


if __name__ == "__main__":
    main(sys.argv[1:])
