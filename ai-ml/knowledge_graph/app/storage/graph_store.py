"""
Stores graph edges as a JSON file inside the same shared data
directory ChromaDB already uses (CHROMA_DB_PATH). This is
deliberately not a new database technology — edges are small,
relationship-only records, so a flat JSON file keeps this module
free of new infrastructure dependencies while still living
alongside the "one shared data location" the rest of the project
already uses.

Not safe for many concurrent writers, but fine for how this module
is used today.
"""
import json
import os
from pathlib import Path
from threading import Lock

from knowledge_graph.app.config import CHROMA_DB_PATH

_EDGES_FILENAME = "knowledge_graph_edges.json"
_lock = Lock()


def _edges_path() -> Path:
    return Path(CHROMA_DB_PATH) / _EDGES_FILENAME


def _read_all() -> list:
    path = _edges_path()
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_all(edges: list) -> None:
    path = _edges_path()
    os.makedirs(path.parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(edges, f, indent=2)


def save_edges(user_id: str, edges: list, node_type: str) -> int:
    """
    Full-replace: removes ALL existing edges of the given node_type
    for this user, then writes the new set. Used by build_graph()'s
    full rebuild — NOT safe to use for incremental updates, since it
    would delete edges you meant to keep. Use append_edges() instead
    when adding to an existing graph rather than rebuilding it.
    """
    with _lock:
        all_edges = _read_all()
        all_edges = [
            e for e in all_edges
            if not (e["user_id"] == user_id and e["node_type"] == node_type)
        ]
        all_edges.extend(edges)
        _write_all(all_edges)
    return len(edges)


def append_edges(user_id: str, new_edges: list, node_type: str) -> int:
    """
    [Task 5] Adds edges without deleting any existing ones — for
    incremental updates when a single new document is added, rather
    than a full graph rebuild. Use save_edges() instead when you
    genuinely want to replace the full edge set (e.g. manual
    /graph/rebuild).
    """
    with _lock:
        all_edges = _read_all()
        all_edges.extend(new_edges)
        _write_all(all_edges)
    return len(new_edges)


def get_edges(user_id: str, node_type: str = None) -> list:
    all_edges = _read_all()
    result = [e for e in all_edges if e["user_id"] == user_id]
    if node_type:
        result = [e for e in result if e["node_type"] == node_type]
    return result


def delete_edges(user_id: str) -> None:
    with _lock:
        all_edges = _read_all()
        all_edges = [e for e in all_edges if e["user_id"] != user_id]
        _write_all(all_edges)