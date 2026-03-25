"""In-memory vector/RAG mocks so tests can run without ChromaDB."""

from __future__ import annotations
import uuid
from typing import Any

class InMemoryVectorStore:
    def __init__(self):
        self._docs = []

    def add(self, content: str, metadata=None, id_: str | None = None) -> str:
        doc_id = id_ or f"exp_{uuid.uuid4().hex[:12]}"
        self._docs.append({"id": doc_id, "content": content, "metadata": metadata or {}})
        return doc_id

    def search(self, query: str, top_k: int = 5, where=None) -> list:
        q = (query or "").lower().split()
        scored = []
        for d in self._docs:
            c = (d.get("content") or "").lower()
            score = sum(1 for w in q if len(w) > 2 and w in c)
            if score > 0:
                scored.append((score, {"id": d["id"], "content": d["content"], "metadata": d.get("metadata", {}), "distance": 0.5}))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:top_k]]

    def delete(self, ids: list) -> None:
        self._docs = [d for d in self._docs if d["id"] not in ids]

class InMemoryRAGCollection:
    def __init__(self):
        self._docs = []

    def count(self) -> int:
        return len(self._docs)

    def add(self, documents: list, metadatas=None, ids=None) -> None:
        for i, doc in enumerate(documents):
            meta = (metadatas or [{}])[i] if metadatas else {}
            doc_id = (ids or [])[i] if ids else f"rag_{uuid.uuid4().hex[:12]}"
            self._docs.append({"id": doc_id, "content": doc, "metadata": meta})

    def query(self, query_texts: list, n_results: int = 5, include=None, **kwargs) -> dict:
        results = {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}
        if not self._docs or not query_texts:
            return results
        q = (query_texts[0] or "").lower().split()
        scored = []
        for d in self._docs:
            c = (d.get("content") or "").lower()
            score = sum(1 for w in q if len(w) > 2 and w in c)
            scored.append((score, d))
        scored.sort(key=lambda x: -x[0])
        for _, d in scored[:n_results]:
            results["ids"][0].append(d["id"])
            results["documents"][0].append(d.get("content", ""))
            results["metadatas"][0].append(d.get("metadata", {})); results["distances"][0].append(0.0)
        return results


class VectorMemoryAdapter:
    """Drop-in for VectorMemory in tests: uses InMemoryVectorStore so Chroma is never loaded."""

    def __init__(self, _path):
        self._impl = InMemoryVectorStore()

    def add(self, content: str, metadata=None, id_: str | None = None) -> str:
        return self._impl.add(content, metadata, id_)

    def search(self, query: str, top_k: int = 5, where=None) -> list:
        return self._impl.search(query, top_k=top_k, where=where)

    def delete(self, ids: list) -> None:
        return self._impl.delete(ids)
