"""
Part B demo: multi-turn conversational RAG with short-term memory.

Default mode runs a scripted 3-4 turn conversation (reviewer-friendly).
Pass --interactive for a live REPL.

Usage:
  python conversational_rag.py
  python conversational_rag.py --interactive
  python conversational_rag.py --k 2
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

# Allow importing helpers from ../rag-engine when run as a script
RAG_ENGINE_DIR = Path(__file__).resolve().parent.parent / "rag-engine"
if str(RAG_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(RAG_ENGINE_DIR))

from chunker import chunk_file  # noqa: E402
from vector_store import (  # noqa: E402
    add_chunks,
    create_collection,
    format_retrieved_chunks,
    load_embedding_model,
    retrieve,
)

DATA_FILE = RAG_ENGINE_DIR / "data" / "photosynthesis_overview.txt"
HISTORY_TURN_CAP = 4  # keep last N user/assistant message pairs (≈ 2*N messages)

SCRIPTED_TURNS = [
    "What is photosynthesis?",
    "Where does it happen in the plant?",
    "What about the second stage you mentioned?",
    "Why does that matter for Earth's atmosphere?",
]


def recent_history(history: list[dict], max_turns: int = HISTORY_TURN_CAP) -> list[dict]:
    """Return the last max_turns user/assistant pairs (up to 2 * max_turns messages)."""
    max_messages = max_turns * 2
    return history[-max_messages:]


def build_messages(
    history: list[dict],
    retrieved_text: str,
    question: str,
) -> list[dict]:
    """
    System + prior turns as real role messages + latest user message with
    retrieved chunk(s) and the current question.
    """
    messages: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are a helpful study assistant. Answer using the provided "
                "reference chunk(s) and the conversation context. If a follow-up "
                "refers to something mentioned earlier (for example 'the second "
                "stage'), use prior turns to resolve it. If the chunk(s) and "
                "history together still lack the answer, say so."
            ),
        }
    ]
    messages.extend(recent_history(history))
    messages.append(
        {
            "role": "user",
            "content": (
                f"Reference chunk(s):\n{retrieved_text}\n\n"
                f"Current question: {question}"
            ),
        }
    )
    return messages


def ask_once(
    client: Groq,
    collection,
    embedding_model,
    history: list[dict],
    question: str,
    n_results: int,
) -> str:
    results = retrieve(collection, embedding_model, question, n_results=n_results)
    documents = results["documents"]
    retrieved_text = format_retrieved_chunks(documents) if documents else "(none)"

    print(f"\nHistory length (messages): {len(history)}")
    print(f"Retrieved {len(documents)} chunk(s):")
    for i, doc in enumerate(documents):
        chunk_id = results["ids"][i] if results["ids"] else f"result_{i}"
        preview = " ".join(doc.split()[:20])
        print(f"  - {chunk_id}: {preview}...")

    messages = build_messages(history, retrieved_text, question)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0.3,
    )
    answer = response.choices[0].message.content or ""

    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})
    # Cap stored history after append
    capped = recent_history(history)
    history.clear()
    history.extend(capped)

    return answer


def setup_store():
    print(f"Loading document: {DATA_FILE.name}")
    chunks = chunk_file(DATA_FILE)
    print(f"Created {len(chunks)} chunk(s)")

    print("Loading embedding model...")
    embedding_model = load_embedding_model()
    collection = create_collection(name="study_chunks_memory")
    print("Embedding chunks and storing in ChromaDB...")
    add_chunks(collection, embedding_model, chunks)
    return collection, embedding_model


def run_scripted(client: Groq, collection, embedding_model, n_results: int) -> None:
    history: list[dict] = []
    print("\n=== Scripted conversation demo ===\n")
    for turn_number, question in enumerate(SCRIPTED_TURNS, start=1):
        print(f"\n----- Turn {turn_number} -----")
        print(f"User: {question}")
        answer = ask_once(
            client, collection, embedding_model, history, question, n_results
        )
        print(f"\nAssistant: {answer}")


def run_interactive(client: Groq, collection, embedding_model, n_results: int) -> None:
    history: list[dict] = []
    print("\n=== Interactive mode (type 'quit' to exit) ===\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break
        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            print("Goodbye.")
            break
        answer = ask_once(
            client, collection, embedding_model, history, question, n_results
        )
        print(f"\nAssistant: {answer}\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Conversational RAG with memory")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Live REPL instead of the scripted demo",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=1,
        help="Number of chunks to retrieve per turn (default: 1)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env")
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
    load_dotenv()
    args = parse_args(argv)

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Source document not found: {DATA_FILE}")

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")

    collection, embedding_model = setup_store()
    client = Groq(api_key=api_key)
    n_results = max(1, args.k)

    if args.interactive:
        run_interactive(client, collection, embedding_model, n_results)
    else:
        run_scripted(client, collection, embedding_model, n_results)


if __name__ == "__main__":
    main(sys.argv[1:])
