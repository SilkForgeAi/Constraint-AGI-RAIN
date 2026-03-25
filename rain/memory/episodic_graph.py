"""Graph-Based Episodic Memory — continuous-time consolidation beyond context limits.

Instead of feeding the LLM raw text logs, Rain translates past experiences into
a knowledge graph (nodes and edges). When the LLM encounters a problem, Rain
queries the graph for exact logical dependencies and injects a mathematically
dense prompt. Fixes context-window forgetting and improves retrieval precision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Relation types for edges
RELATION_CAUSES = "causes"
RELATION_ENABLES = "enables"
RELATION_DEPENDS_ON = "depends_on"
RELATION_CONTRADICTS = "contradicts"
RELATION_RELATES_TO = "relates_to"


@dataclass
class GraphNode:
    """Single node in the episodic graph."""
    id: str
    content: str
    node_type: str  # "experience" | "fact" | "skill" | "lesson" | "belief"
    timestamp: str = ""
    importance: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


class EpisodicGraph:
    """
    In-memory graph of experiences: nodes and directed edges (causes, enables, depends_on, etc.).
    Query by logical dependency to get a dense, structured context for the LLM.
    """

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[tuple[str, str, str]] = []  # (from_id, to_id, relation)
        self._incoming: dict[str, list[tuple[str, str]]] = {}  # to_id -> [(from_id, relation)]

    def add_node(self, nid: str, content: str, node_type: str = "experience", importance: float = 0.5, timestamp: str = "", metadata: dict | None = None) -> None:
        self._nodes[nid] = GraphNode(
            id=nid,
            content=(content or "")[:2000],
            node_type=node_type,
            timestamp=timestamp,
            importance=importance,
            metadata=dict(metadata or {}),
        )

    def add_edge(self, from_id: str, to_id: str, relation: str = RELATION_RELATES_TO) -> None:
        if from_id in self._nodes and to_id in self._nodes:
            self._edges.append((from_id, to_id, relation))
            self._incoming.setdefault(to_id, []).append((from_id, relation))

    def get_node(self, nid: str) -> GraphNode | None:
        return self._nodes.get(nid)

    def get_dependencies(self, nid: str) -> list[tuple[str, str]]:
        """Return [(node_id, relation)] that this node depends on (incoming edges)."""
        return list(self._incoming.get(nid, []))

    def query_dependencies(
        self,
        seed_content: str,
        max_nodes: int = 10,
        relation_filter: list[str] | None = None,
    ) -> str:
        """
        Find nodes whose content is relevant to seed_content (simple substring match),
        then expand along incoming edges to collect logical dependencies. Return a
        dense, structured prompt (nodes + edges) for the LLM.
        """
        if not seed_content or not seed_content.strip():
            return ""
        seed_lower = seed_content.lower()
        # Seed nodes: content contains any significant word from seed (words len >= 4)
        words = [w for w in seed_lower.split() if len(w) >= 4][:5]
        if not words:
            words = seed_lower.split()[:5]
        seed_ids: set[str] = set()
        for nid, node in self._nodes.items():
            c = (node.content or "").lower()
            if any(w in c for w in words):
                seed_ids.add(nid)
        if not seed_ids:
            return ""

        # Expand backward along incoming edges (dependencies)
        included: set[str] = set(seed_ids)
        frontier = list(seed_ids)
        while frontier and len(included) < max_nodes:
            nid = frontier.pop()
            for from_id, rel in self.get_dependencies(nid):
                if relation_filter and rel not in relation_filter:
                    continue
                if from_id not in included:
                    included.add(from_id)
                    frontier.append(from_id)

        # Build dense output: list nodes and then edges (logical dependencies)
        lines = ["Logical dependency context (graph):"]
        for nid in included:
            node = self._nodes.get(nid)
            if not node:
                continue
            content_preview = (node.content or "")[:150].replace("\n", " ")
            lines.append(f"  [{nid}] ({node.node_type}, importance={node.importance:.2f}): {content_preview}")
        lines.append("Dependencies:")
        for from_id, to_id, rel in self._edges:
            if to_id in included and from_id in included:
                lines.append(f"  {from_id} --[{rel}]--> {to_id}")
        return "\n".join(lines)

    def sync_from_memory_store(self, store: Any) -> None:
        """
        Populate graph from MemoryStore: recent experiences + relates_to/contradicts from metadata.
        Call after remember_experience or periodically. store must have recall_similar and timeline.
        """
        try:
            recent = store.recall_recent(limit=30, namespace=None)
            for e in recent:
                content = (e.get("content") or "").strip()
                if not content:
                    continue
                meta = e.get("metadata") or {}
                if isinstance(meta, str):
                    try:
                        import json
                        meta = json.loads(meta)
                    except Exception:
                        meta = {}
                vid = str(e.get("id") or e.get("vector_id") or len(self._nodes))
                importance = float(meta.get("importance", 0.5))
                node_type = meta.get("type", "experience")
                self.add_node(vid, content, node_type=node_type, importance=importance, metadata=meta)
                for rel_id in (meta.get("relates_to") or "").split(","):
                    rel_id = rel_id.strip()
                    if rel_id:
                        self.add_edge(rel_id, vid, RELATION_RELATES_TO)
                for cid in (meta.get("contradicts") or []):
                    if cid:
                        self.add_edge(str(cid), vid, RELATION_CONTRADICTS)
        except Exception:
            pass
