"""RAG (Retrieval-Augmented Generation) — document corpus for grounded responses.

Documents are embedded and stored; query_rag retrieves relevant chunks.
Chunked ingestion for long documents. Gated by RAIN_RAG_ENABLED.
Uses ChromaDB with a separate collection from memory.
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

# Default path for RAG collection (separate from experience memory)
_RAG_COLLECTION = "rag_documents"


def _get_rag_collection(base_path: Path):
    """Get or create the RAG ChromaDB collection."""
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    rag_dir = base_path / "rag"
    rag_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(rag_dir),
        settings=Settings(anonymized_telemetry=False),
    )
    try:
        coll = client.get_collection(_RAG_COLLECTION)
    except Exception:
        ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        coll = client.create_collection(
            _RAG_COLLECTION,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
    return coll


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks (by characters)."""
    if not text or chunk_size <= 0:
        return [text] if text else []
    step = max(1, chunk_size - overlap)
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step
    return chunks


def add_document(content: str, source: str = "", base_path: Path | None = None) -> str:
    """Add a document to the RAG corpus (single chunk if short). Returns document id."""
    from rain.config import DATA_DIR
    path = base_path or DATA_DIR
    coll = _get_rag_collection(path)
    doc_id = f"rag_{uuid.uuid4().hex[:12]}"
    meta: dict[str, Any] = {}
    if source:
        meta["source"] = str(source)[:200]
    coll.add(documents=[content[:50000]], metadatas=[meta], ids=[doc_id])
    return doc_id


def add_document_chunked(
    content: str,
    source: str = "",
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
    base_path: Path | None = None,
) -> list[str]:
    """Add a long document as multiple chunks. Returns list of chunk ids."""
    from rain.config import DATA_DIR, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP
    path = base_path or DATA_DIR
    size = chunk_size if chunk_size is not None else RAG_CHUNK_SIZE
    overlap = chunk_overlap if chunk_overlap is not None else RAG_CHUNK_OVERLAP
    chunks = _chunk_text(content[:500000], size, overlap)
    if not chunks:
        return []
    coll = _get_rag_collection(path)
    ids = []
    base_id = f"rag_{uuid.uuid4().hex[:12]}"
    for i, ch in enumerate(chunks):
        if not ch.strip():
            continue
        cid = f"{base_id}_{i}"
        meta: dict[str, Any] = {"chunk_index": i, "total_chunks": len(chunks)}
        if source:
            meta["source"] = str(source)[:200]
        coll.add(documents=[ch], metadatas=[meta], ids=[cid])
        ids.append(cid)
    return ids


def _run_single_query(coll: Any, query: str, k: int, count: int) -> list[dict]:
    results = coll.query(
        query_texts=[query],
        n_results=min(k, count),
        include=["documents", "metadatas", "distances", "ids"],
    )
    out: list[dict] = []
    if results.get("documents") and results["documents"][0]:
        docs = results["documents"][0]
        metas = results.get("metadatas", [[]])[0] or [{}] * len(docs)
        dists = results.get("distances", [[]])[0] or [0.0] * len(docs)
        ids = results.get("ids", [[]])[0] or [""] * len(docs)
        for doc, meta, dist, doc_id in zip(docs, metas, dists, ids):
            out.append({
                "content": doc or "",
                "source": (meta or {}).get("source", ""),
                "distance": float(dist) if dist is not None else 0.0,
                "id": doc_id or "",
            })
    return out


def _expand_queries(query: str, max_expansions: int = 2) -> list[str]:
    q = (query or "").strip()
    if not q:
        return []
    expansions: list[str] = []
    lower = q.lower()

    subs = [
        (r"\bproof\b", "derivation"),
        (r"\bderive\b", "formal derivation"),
        (r"\bmass gap\b", "spectral gap"),
        (r"\bconfinement\b", "wilson loop area law"),
        (r"\bbeta function\b", "renormalization group beta"),
        (r"\blattice\b", "lattice gauge theory"),
    ]
    for pat, rep in subs:
        if re.search(pat, lower):
            expansions.append(re.sub(pat, rep, q, flags=re.I))

    expansions.append(f"key equations and definitions: {q}")
    expansions.append(f"formal statement and assumptions: {q}")

    seen: set[str] = set()
    uniq: list[str] = []
    for e in expansions:
        ee = e.strip()
        if ee and ee.lower() not in seen and ee.lower() != lower:
            seen.add(ee.lower())
            uniq.append(ee)
    return uniq[:max_expansions]



def _tokenize_for_rank(text: str) -> list[str]:
    import re
    return [tok for tok in re.findall(r"[a-zA-Z0-9_]+", (text or "").lower()) if len(tok) > 2]


def _rerank_hits(query: str, hits: list[dict], keep_n: int) -> list[dict]:
    """Cheap lexical reranker over merged vector hits."""
    import re
    if not hits:
        return []

    q_tokens = set(_tokenize_for_rank(query))
    if not q_tokens:
        return hits[:keep_n]

    ranked: list[tuple[float, dict]] = []
    for h in hits:
        content = (h.get("content") or "")
        c_tokens = set(_tokenize_for_rank(content))

        overlap = len(q_tokens & c_tokens) / max(1, len(q_tokens))
        eq_bonus = 0.08 if re.search(r"[\d\)\]]\s*[\+\-\*\/\^=]\s*[\d\(\[]", content) else 0.0

        dist = float(h.get("distance", 1.0))
        dist_score = 1.0 - min(1.0, dist / 2.0)

        score = (0.55 * overlap) + (0.35 * dist_score) + eq_bonus
        ranked.append((score, h))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return [h for _, h in ranked[:keep_n]]


def _dedupe_rank(results: list[dict], top_k: int) -> list[dict]:

    best_by_key: dict[tuple[str, str, str], dict] = {}
    for r in results:
        content = (r.get("content") or "").strip()
        key = (
            str(r.get("id") or "").strip(),
            str(r.get("source") or "").strip(),
            content[:120],
        )
        prev = best_by_key.get(key)
        if prev is None or float(r.get("distance", 999.0)) < float(prev.get("distance", 999.0)):
            best_by_key[key] = r
    merged = list(best_by_key.values())
    merged.sort(key=lambda x: float(x.get("distance", 999.0)))
    return merged[:top_k]


def query_rag(
    query: str,
    top_k: int | None = None,
    base_path: Path | None = None,
    adaptive: bool = True,
) -> list[dict]:
    """
    Retrieve documents relevant to the query from the RAG corpus.
    Returns list of {content, source, distance, id}.

    adaptive=True enables lightweight query expansion + merged ranking.
    """
    from rain.config import DATA_DIR, RAG_TOP_K
    path = base_path or DATA_DIR
    k = top_k if top_k is not None else RAG_TOP_K
    coll = _get_rag_collection(path)
    count = coll.count()
    if count == 0:
        return []

    if not adaptive:
        return _run_single_query(coll, query, k, count)

    queries = [query] + _expand_queries(query, max_expansions=2)
    all_hits: list[dict] = []
    # Pull a wider pool first, then rerank down to k.
    per_query_k = min(max(8, k * 2), count)
    for q in queries:
        all_hits.extend(_run_single_query(coll, q, per_query_k, count))

    merged = _dedupe_rank(all_hits, top_k=min(max(k * 3, 12), count))
    return _rerank_hits(query, merged, keep_n=k)


def retrieve(
    query: str,
    top_k: int | None = None,
    base_path: Path | None = None,
) -> list[dict]:
    """
    Unified RAG retrieval. Returns list of {text, source, score} (score = 1 - normalized distance).
    Use from agent or tools to get consistent format.
    """
    raw = query_rag(query, top_k=top_k, base_path=base_path, adaptive=True)
    out = []
    for r in raw:
        dist = r.get("distance", 1.0)
        score = 1.0 - min(1.0, dist / 2.0)
        out.append({
            "text": r.get("content", ""),
            "source": r.get("source", ""),
            "score": round(score, 4),
        })
    return out
