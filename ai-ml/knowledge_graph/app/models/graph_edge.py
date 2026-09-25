"""
Represents a relationship (edge) between two nodes in the graph.
"""
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class GraphEdge:
    user_id: str
    source_id: str
    target_id: str
    node_type: str          # "document" or "topic"
    similarity: float
    source_title: str
    target_title: str
    label: Optional[str] = None            # keyword-based explanation (existing)
    relationship_type: str = "related_to"  # NEW — placeholder until LLM classification (task 3) fills this in with real types like "prerequisite_of", "example_of", etc.

    def to_dict(self) -> dict:
        return asdict(self)