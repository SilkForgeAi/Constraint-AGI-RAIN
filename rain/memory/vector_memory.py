"""Vector memory — experience embeddings for semantic retrieval."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any


def _sanitize_metadata(meta: dict[str, Any] | None) -> dict[str, str | int | float | bool]:
    """ChromaDB only accepts str, int, float, bool in metadata."""
    if not meta:
        return {}
    out: dict[str, str | int | float | bool] = {}
    for k, v in meta.items():
        if isinstance(v, (str, int, float, bool)):
            out[k] = v
        else:
            out[k] = str(v)
    return out


class VectorMemory:
    """Stores experiences as embeddings for similarity search. Lazy-loads ChromaDB on first use."""

    def __init__(self, persist_path: Path):
        self._path = persist_path
        self._client = None
        self._collection = None

    def _ensure_loaded(self) -> None:
        if self._collection is not None:
            return
        import chromadb
        from chromadb.config import Settings
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        self._path.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=str(self._path),
            settings=Settings(anonymized_telemetry=False),
        )
        # If collection exists, use it without passing embedding_function (avoids conflict
        # when persisted used "default" and we now use sentence_transformer).
        try:
            self._collection = self._client.get_collection("experiences")
        except Exception:
            ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
            self._collection = self._client.create_collection(
                "experiences",
                embedding_function=ef,
                metadata={"hnsw:space": "cosine"},
            )

    def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        id_: str | None = None,
    ) -> str:
        """Store an experience. Returns assigned id."""
        self._ensure_loaded()
        meta = _sanitize_metadata(metadata)
        doc_id = id_ or f"exp_{uuid.uuid4().hex[:12]}"
        self._collection.add(
            documents=[content],
            metadatas=[meta],
            ids=[doc_id],
        )
        return doc_id

    def search(
        self,
        query: str,
        top_k: int = 5,
        where: dict | None = None,
    ) -> list[dict]:
        """Retrieve similar experiences by semantic query. Optional where filter on metadata."""
        self._ensure_loaded()
        count = self._collection.count()
        if count == 0:
            return []
        kwargs: dict = {"query_texts": [query], "n_results": min(top_k, count)}
        if where:
            kwargs["where"] = where
        results = self._collection.query(**kwargs)
        out = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, ids, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["ids"][0],
                results["distances"][0] if results.get("distances") else [0] * len(results["documents"][0]),
            ):
                out.append({
                    "content": doc,
                    "metadata": meta or {},
                    "id": ids,
                    "distance": float(dist) if dist else 0,
                })
        return out

    def get_all_metadata(self) -> list[tuple[str, dict]]:
        """Get all (id, metadata) for consolidation. Returns [(id, meta), ...]."""
        self._ensure_loaded()
        try:
            result = self._collection.get(include=["metadatas", "ids"])
            ids = result.get("ids") or []
            metas = result.get("metadatas") or [{}] * len(ids)
            return list(zip(ids, metas))
        except Exception:
            return []

    def list_all(self, limit: int = 500) -> list[dict]:
        """List all experiences for audit. Returns [{id, content, metadata}]."""
        self._ensure_loaded()
        try:
            count = self._collection.count()
            if count == 0:
                return []
            result = self._collection.get(
                include=["documents", "metadatas", "ids"],
                limit=min(limit, count),
            )
            ids = result.get("ids") or []
            docs = result.get("documents") or [""] * len(ids)
            metas = result.get("metadatas") or [{}] * len(ids)
            return [
                {"id": i, "content": d or "", "metadata": m or {}}
                for i, d, m in zip(ids, docs, metas)
            ]
        except Exception:
            return []

    def delete(self, ids: list[str]) -> None:
        """Delete experiences by id. Safe to call with non-existent ids."""
        if not ids:
            return
        self._ensure_loaded()
        self._collection.delete(ids=ids)

    def clear(self) -> None:
        """Clear all vector memory (use with care)."""
        from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
        self._ensure_loaded()
        ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        self._client.delete_collection("experiences")
        self._collection = self._client.get_or_create_collection(
            "experiences",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
