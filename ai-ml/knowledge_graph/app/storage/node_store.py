"""
[Task 4] Stores per-node metadata (currently: definitions) alongside
the existing edge storage in graph_store.py. Same JSON-file-in-shared-
directory pattern, kept as a separate file/store since nodes and
edges have different lifecycles: a node's definition is generated
once per document, while edges can be added/removed independently.
"""
import json
import os
from pathlib import Path
from threading import Lock

from knowledge_graph.app.config import CHROMA_DB_PATH

_NODES_FILENAME = "knowledge_graph_node_metadata.json"
_lock = Lock()


def _path() -> Path:
    return Path(CHROMA_DB_PATH) / _NODES_FILENAME


def _read_all() -> dict:
    p = _path()
    if not p.exists():
        return {}
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_all(data: dict) -> None:
    p = _path()
    os.makedirs(p.parent, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def save_node_metadata(user_id: str, document_id: str, definition: str) -> None:
    """
    Stores a document's definition, keyed by user_id + document_id so
    it can be looked up per-user without collisions across users.
    """
    key = f"{user_id}::{document_id}"
    with _lock:
        data = _read_all()
        data[key] = {"definition": definition}
        _write_all(data)


def get_node_metadata(user_id: str, document_id: str) -> dict:
    """
    Returns {"definition": str}. Returns {"definition": ""} if no
    metadata has been generated for this document yet (e.g. it was
    ingested before this feature existed) — callers should treat an
    empty definition as "not available" rather than an error.
    """
    key = f"{user_id}::{document_id}"
    data = _read_all()
    return data.get(key, {"definition": ""})


def delete_node_metadata(user_id: str) -> None:
    """Removes all node metadata for a user (mirrors delete_edges())."""
    prefix = f"{user_id}::"
    with _lock:
        data = _read_all()
        data = {k: v for k, v in data.items() if not k.startswith(prefix)}
        _write_all(data)