"""
Integration tests for GraphService, against an isolated, in-memory
ChromaDB collection — NOT the real shared store.

This isolation matters: an earlier version of this file used the
real persistent collection (embedding.chroma_store.get_collection())
directly, which wrote 16-dimension synthetic test vectors into the
actual shared store. Since a Chroma collection's dimension is fixed
by its first insert, this locked the real collection to 16
dimensions — incompatible with the real embedding model's 384
dimensions, breaking real ingestion. This version fixes that by
patching get_collection() to use a fresh, in-memory client for every
test, so nothing here ever touches real data.

Run: pytest knowledge_graph/tests/test_graph_service.py
"""
import numpy as np
import pytest
import chromadb

from knowledge_graph.app.builders import document_graph_builder
from knowledge_graph.app.services.graph_service import GraphService


@pytest.fixture(autouse=True)
def isolated_chroma_collection(monkeypatch):
    """
    Redirects document_graph_builder's get_collection() to a fresh,
    in-memory ChromaDB client for the duration of each test. Applied
    automatically to every test in this file — no test here should
    ever be able to touch the real persistent store.
    """
    test_client = chromadb.EphemeralClient()

    def fake_get_collection(name="study_chunks", path=None):
        return test_client.get_or_create_collection(name=name)

    monkeypatch.setattr(document_graph_builder, "get_collection", fake_get_collection)


def _make_vec(base: float, dim: int = 384, seed: int = 0) -> list:
    """
    dim defaults to 384 (matching the real embedding model's output
    size) specifically so a dimension mismatch like the one that
    corrupted the real store can't recur even if isolation is ever
    accidentally removed.
    """
    rng = np.random.default_rng(seed)
    return rng.normal(loc=base, scale=0.03, size=dim).tolist()


@pytest.fixture
def seeded_user():
    """Inserts two related documents and one unrelated document for a test user."""
    user_id = "pytest_user"
    collection = document_graph_builder.get_collection()

    rows = [
        ("docA", 0, "ML Basics", "Neural networks learn from data.", 0.8, 1),
        ("docA", 1, "ML Basics", "Training uses gradient descent.", 0.8, 2),
        ("docB", 0, "Deep Learning", "Gradient descent trains neural networks.", 0.82, 3),
        ("docC", 0, "Cooking", "Bread requires yeast and flour.", -0.8, 4),
    ]
    ids, embeddings, documents, metadatas = [], [], [], []
    for doc_id, idx, title, text, base, seed in rows:
        ids.append(f"{doc_id}_{idx}")
        embeddings.append(_make_vec(base, seed=seed))
        documents.append(text)
        metadatas.append({"user_id": user_id, "document_id": doc_id, "document": title, "chunk_index": idx})

    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    return user_id


def test_build_graph_links_related_documents(seeded_user):
    service = GraphService()
    result = service.build_graph(seeded_user)
    assert result["document_edges_created"] >= 1

    graph = service.get_graph(seeded_user)
    doc_edges = [e for e in graph["edges"] if e["node_type"] == "document"]
    titles = {(e["source_title"], e["target_title"]) for e in doc_edges}

    assert ("ML Basics", "Deep Learning") in titles or ("Deep Learning", "ML Basics") in titles


def test_build_graph_does_not_link_unrelated_documents(seeded_user):
    service = GraphService()
    service.build_graph(seeded_user)
    graph = service.get_graph(seeded_user)

    doc_edges = [e for e in graph["edges"] if e["node_type"] == "document"]
    cooking_involved = any(
        "Cooking" in (e["source_title"], e["target_title"]) for e in doc_edges
    )
    assert not cooking_involved


def test_get_graph_nodes_match_documents(seeded_user):
    service = GraphService()
    graph = service.get_graph(seeded_user)
    titles = {n["title"] for n in graph["nodes"]}
    assert titles == {"ML Basics", "Deep Learning", "Cooking"}


def test_delete_graph_clears_edges(seeded_user):
    service = GraphService()
    service.build_graph(seeded_user)
    service.delete_graph(seeded_user)

    graph = service.get_graph(seeded_user)
    assert graph["edges"] == []


def test_user_with_no_documents_does_not_crash():
    service = GraphService()
    result = service.build_graph("nobody_has_this_id")
    assert result["document_edges_created"] == 0
    assert result["topic_edges_created"] == 0


def test_empty_user_id_raises():
    service = GraphService()
    with pytest.raises(ValueError):
        service.get_graph("")


def test_no_duplicate_document_edges(seeded_user):
    service = GraphService()
    service.build_graph(seeded_user)
    graph = service.get_graph(seeded_user)

    doc_edges = [e for e in graph["edges"] if e["node_type"] == "document"]
    pairs_seen = [frozenset((e["source_id"], e["target_id"])) for e in doc_edges]
    assert len(pairs_seen) == len(set(pairs_seen)), "duplicate edge detected"


def test_no_self_referencing_edges(seeded_user):
    service = GraphService()
    service.build_graph(seeded_user)
    graph = service.get_graph(seeded_user)

    for e in graph["edges"]:
        assert e["source_id"] != e["target_id"], f"self-link found: {e}"