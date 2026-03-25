"""Unified memory store — vector + symbolic + timeline. 10/10 memory."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .contradiction import filter_contradicting
from .importance import score_importance
from .policy import should_store
from .symbolic_memory import SymbolicMemory
from .timeline_memory import TimelineMemory

from rain.safety.retrieval_sanitizer import sanitize_chunk


# Minimum importance to store (0–1). Below this, skip.
MIN_IMPORTANCE_TO_STORE = 0.35

# For retrieval: weight semantic (1-distance) vs importance vs recency
RETRIEVAL_WEIGHTS = {"semantic": 0.5, "importance": 0.3, "recency": 0.2}

# Minimum weighted score to include in context (avoid low-relevance contamination)
MIN_RETRIEVAL_SCORE = 0.25


def _vector_disabled() -> bool:
    """True when Chroma/vector should never be loaded (avoids segfaults on some systems)."""
    try:
        from rain import config
        return getattr(config, "DISABLE_VECTOR_MEMORY", False)
    except Exception:
        return False


class MemoryStore:
    """Single interface to all Rain memory systems. Vector memory loads lazily."""

    def __init__(self, base_path: Path):
        self._base_path = base_path
        self.symbolic = SymbolicMemory(base_path / "symbolic.db")
        self.timeline = TimelineMemory(base_path / "timeline.db")
        self._vector: Any = None
        self._vector_failed = False

    @property
    def vector(self) -> "VectorMemory":
        if _vector_disabled():
            self._vector_failed = True
            raise RuntimeError("Vector memory is disabled (RAIN_DISABLE_VECTOR_MEMORY)")
        if self._vector is None and not self._vector_failed:
            try:
                from .vector_memory import VectorMemory
                vec_dir = self._base_path / "vector"
                vec_dir.mkdir(parents=True, exist_ok=True)
                self._vector = VectorMemory(vec_dir)
            except Exception:
                self._vector_failed = True
                raise
        return self._vector

    def _fallback_retrieval(self, query: str, top_k: int, namespace: str | None) -> list[dict]:
        """When vector DB is unavailable: use recent timeline + simple keyword overlap."""
        raw = self.recall_recent(limit=50, event_type="experience", namespace=namespace)
        q_lower = query.lower().split()
        scored = []
        for e in raw:
            c = (e.get("content") or "")[:500]
            if not c:
                continue
            c_lower = c.lower()
            score = sum(1 for w in q_lower if len(w) > 2 and w in c_lower)
            if score > 0:
                scored.append((score, {"content": c, "metadata": e.get("metadata", {}), "id": e.get("id", "")}))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:top_k]]

    def remember_experience(self, content: str, metadata: dict | None = None, namespace: str | None = None) -> str | None:
        """Store in vector memory and log to timeline. Importance + contradiction aware.
        namespace: 'chat' | 'autonomy' | 'test' — isolates memories; chat never sees test/autonomy."""
        if not should_store(content, metadata):
            return None
        importance = score_importance(content, metadata)
        if importance < MIN_IMPORTANCE_TO_STORE:
            return None
        meta = dict(metadata or {})
        meta["importance"] = round(importance, 3)
        meta["timestamp"] = datetime.now().isoformat()
        if namespace:
            meta["session_type"] = namespace
        # Contradiction check + integrative linking (relate new to similar past)
        vid = None
        if not _vector_disabled():
            try:
                where = {"session_type": namespace} if namespace else None
                similar = self.vector.search(content, top_k=5, where=where)
                contradicting = filter_contradicting(content, similar)
                if contradicting:
                    meta["contradicts"] = [c.get("id", "") for c in contradicting[:3]]
                contradict_ids = {c.get("id", "") for c in contradicting}
                non_contradicting_ids = [s.get("id", "") for s in similar if s.get("id") and s.get("id") not in contradict_ids]
                if non_contradicting_ids:
                    meta["relates_to"] = ",".join(non_contradicting_ids[:5])
                vid = self.vector.add(content, meta)
            except Exception:
                self._vector_failed = True
        self.timeline.add("experience", content, {"vector_id": vid, "importance": importance, **(meta or {})})
        # Sync-on-write: add to episodic graph immediately when enabled (no delay until next query)
        try:
            from rain.config import EPISODIC_GRAPH_CONTEXT
            if EPISODIC_GRAPH_CONTEXT and vid:
                g = self._ensure_episodic_graph()
                if g:
                    g.add_node(
                        str(vid),
                        content,
                        node_type=meta.get("type", "experience"),
                        importance=importance,
                        timestamp=meta.get("timestamp", ""),
                        metadata=meta,
                    )
                    for rel_id in (meta.get("relates_to") or "").split(","):
                        rel_id = (rel_id or "").strip()
                        if rel_id:
                            g.add_edge(rel_id, str(vid), "relates_to")
                    for cid in (meta.get("contradicts") or []):
                        if cid:
                            g.add_edge(str(cid), str(vid), "contradicts")
        except Exception:
            pass
        return vid

    def remember_fact(self, key: str, value: Any, kind: str = "fact") -> None:
        """Store in symbolic memory."""
        self.symbolic.set(key, value, kind)
        self.timeline.add("fact", f"{key}={value}", {"key": key, "kind": kind})

    def recall_similar(
        self,
        query: str,
        top_k: int = 5,
        use_weighted: bool = True,
        namespace: str | None = None,
    ) -> list[dict]:
        """Semantic search. If use_weighted, re-rank by importance + recency.
        namespace: only retrieve experiences with this session_type (chat/autonomy/test)."""
        where = None
        if namespace == "chat":
            where = {"session_type": "chat"}
        elif namespace == "autonomy":
            where = {"session_type": {"$in": ["chat", "autonomy"]}}
        elif namespace == "test":
            where = {"session_type": "test"}
        if _vector_disabled():
            return self._fallback_retrieval(query, top_k, namespace)
        try:
            raw = self.vector.search(
                query,
                top_k=top_k * 2 if use_weighted else top_k,
                where=where,
            )
        except Exception:
            self._vector_failed = True
            return self._fallback_retrieval(query, top_k, namespace)
        if not use_weighted or not raw:
            return raw[:top_k]
        # Weighted scoring: semantic + importance + recency
        now = datetime.now()
        scored = []
        for r in raw:
            dist = r.get("distance", 1.0)
            meta = r.get("metadata") or {}
            imp = float(meta.get("importance", 0.5))
            ts = meta.get("timestamp", "")
            recency = 0.5
            if ts:
                try:
                    from datetime import date
                    date_part = ts[:10]
                    stored = datetime.strptime(date_part, "%Y-%m-%d").date()
                    delta = (now.date() - stored).days
                    recency = 1.0 / (1.0 + max(0, delta) / 7)
                except Exception:
                    pass
            semantic = 1.0 - min(1.0, dist / 2.0)
            total = (
                RETRIEVAL_WEIGHTS["semantic"] * semantic
                + RETRIEVAL_WEIGHTS["importance"] * imp
                + RETRIEVAL_WEIGHTS["recency"] * recency
            )
            if total >= MIN_RETRIEVAL_SCORE:
                scored.append((total, r))
        scored.sort(key=lambda x: -x[0])
        results = [r for _, r in scored[:top_k]]

        # Knowledge updating: exclude contradicted experiences (newer info supersedes)
        contradicted_ids: set[str] = set()
        for r in results:
            meta = r.get("metadata") or {}
            for cid in meta.get("contradicts") or []:
                if cid:
                    contradicted_ids.add(str(cid))
        if contradicted_ids:
            results = [r for r in results if r.get("id", "") not in contradicted_ids]

        return results

    def remember_skill(self, procedure: str, namespace: str | None = None) -> str | None:
        """Store procedural knowledge. High importance."""
        meta = {"type": "skill"}
        if namespace:
            meta["session_type"] = namespace
        return self.remember_experience(procedure, metadata=meta, namespace=namespace)

    def recall_skills(self, query: str, top_k: int = 3, namespace: str | None = None) -> list[dict]:
        """Retrieve procedural/skill memories. namespace filters to session_type when set."""
        if _vector_disabled():
            return []
        where: dict = {"type": "skill"}
        if namespace == "chat":
            where = {"type": "skill", "session_type": "chat"}
        elif namespace == "autonomy":
            where = {"type": "skill", "session_type": {"$in": ["chat", "autonomy"]}}
        elif namespace == "test":
            where = {"type": "skill", "session_type": "test"}
        try:
            return self.vector.search(query, top_k, where=where)
        except Exception:
            self._vector_failed = True
            return []

    def recall_fact(self, key: str, kind: str | None = None) -> Any:
        """Look up a fact."""
        return self.symbolic.get(key, kind)

    def recall_recent(
        self,
        limit: int = 20,
        event_type: str | None = None,
        namespace: str | None = None,
    ) -> list[dict]:
        """Get recent timeline events. namespace filters by metadata.session_type."""
        raw = self.timeline.recent(limit=limit * 3 if namespace else limit, event_type=event_type)
        if not namespace:
            return raw[:limit]
        # Filter by session_type; exclude legacy (no session_type) from chat
        filtered = []
        for e in raw:
            meta = e.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    import json
                    meta = json.loads(meta)
                except Exception:
                    meta = {}
            st = meta.get("session_type", "")
            if namespace == "chat":
                if st != "chat":
                    continue
            elif namespace == "autonomy":
                if st and st not in ("chat", "autonomy"):
                    continue
            elif namespace == "test":
                if st and st != "test":
                    continue
            filtered.append(e)
            if len(filtered) >= limit:
                break
        return filtered

    def forget_experience(self, vector_id: str) -> bool:
        """Remove an experience from vector memory. Logs to timeline for audit. Returns True if deleted."""
        if not _vector_disabled():
            try:
                self.vector.delete([vector_id])
            except Exception:
                self._vector_failed = True
        self.timeline.add("forgotten", f"vector_id={vector_id}", {"vector_id": vector_id})
        return True

    def forget_fact(self, key: str, kind: str | None = None) -> bool:
        """Remove a fact from symbolic memory. Returns True if deleted."""
        deleted = self.symbolic.delete(key, kind)
        if deleted:
            self.timeline.add("fact_forgotten", f"key={key}", {"key": key, "kind": kind or "fact"})
        return deleted

    def _ensure_episodic_graph(self) -> "EpisodicGraph | None":
        """Lazy-init graph-based episodic memory when RAIN_EPISODIC_GRAPH is enabled."""
        try:
            from rain.config import EPISODIC_GRAPH_CONTEXT
            if not EPISODIC_GRAPH_CONTEXT:
                return None
        except Exception:
            return None
        if getattr(self, "_episodic_graph", None) is None:
            from rain.memory.episodic_graph import EpisodicGraph
            self._episodic_graph = EpisodicGraph()
            self._episodic_graph.sync_from_memory_store(self)
        return self._episodic_graph

    def get_context_for_query(
        self,
        query: str,
        max_experiences: int = 5,
        include_skills: bool = True,
        namespace: str | None = None,
    ) -> str:
        """Build context string: user identity first, then weighted retrieval + skills.
        When RAIN_EPISODIC_GRAPH=1, prepends graph-based dependency context (dense logical deps).
        namespace: 'chat' | 'autonomy' | 'test' — only retrieval from that namespace (chat never sees test)."""
        parts = []
        graph = self._ensure_episodic_graph()
        if graph and query:
            graph_ctx = graph.query_dependencies(query, max_nodes=10)
            if graph_ctx:
                parts.append(graph_ctx)
                parts.append("")

        # Always include who the user is (personal memory)
        try:
            from rain.memory.user_identity import recall_user_identity, format_user_identity_context
            identity = recall_user_identity(self)
            ctx = format_user_identity_context(identity)
            if ctx:
                parts.append(ctx)
                parts.append("")
        except Exception:
            pass

        similar = self.recall_similar(query, max_experiences, use_weighted=True, namespace=namespace)
        if similar:
            parts.append("Relevant past experiences:")
            for i, s in enumerate(similar, 1):
                c = sanitize_chunk(s["content"], max_len=200)
                c = c + "..." if len(s["content"]) > 200 else c
                if c and c != "...":
                    parts.append(f"  {i}. {c}")

        if include_skills:
            skills = self.recall_skills(query, top_k=2, namespace=namespace)
            if skills:
                parts.append("\nRelevant skills/procedures:")
                for s in skills:
                    c = sanitize_chunk(s.get("content", ""), max_len=150)
                    if c:
                        parts.append(f"  - {c}")

        # Causal reasoning: add causal links when query asks why/how/cause/effect
        causal_keywords = ["why", "how does", "cause", "effect", "what causes", "led to", "because"]
        if any(k in query.lower() for k in causal_keywords):
            try:
                from rain.memory.causal_memory import recall_causal
                causal_links = recall_causal(self, query, limit=3, namespace=namespace)
                if causal_links:
                    parts.append("\nRelevant causal knowledge:")
                    for cl in causal_links:
                        cause_s = sanitize_chunk(cl.get("cause", ""), max_len=60)
                        effect_s = sanitize_chunk(cl.get("effect", ""), max_len=60)
                        if cause_s or effect_s:
                            parts.append(f"  - {cause_s} → {effect_s}")
            except Exception:
                pass

        # Generalization: analogous past situations (few-shot from memory)
        if len(query) > 80 or any(w in query.lower() for w in ["similar", "like", "analogous", "compare", "apply"]):
            try:
                from rain.learning.generalization import find_analogous, format_few_shot_context
                analogous = find_analogous(self, query, top_k=2, namespace=namespace)
                few_shot = format_few_shot_context(analogous)
                if few_shot:
                    parts.append("\n" + sanitize_chunk(few_shot, max_len=500))
            except Exception:
                pass

        # Structured beliefs with confidence
        try:
            from rain.memory.belief_memory import recall_beliefs
            beliefs = recall_beliefs(self, query, limit=2, namespace=namespace)
            if beliefs:
                parts.append("\nRelevant beliefs (with confidence):")
                for b in beliefs:
                    conf = b.get("confidence", 0.5)
                    claim_s = sanitize_chunk(b.get("claim", ""), max_len=100)
                    if claim_s:
                        parts.append(f"  - [{conf:.0%}] {claim_s}")
        except Exception:
            pass

        try:
            from rain.learning.lessons import recall_lessons
            lessons = recall_lessons(self, query, limit=2, namespace=namespace)
            if lessons:
                parts.append("\nRelevant lessons:")
                for lec in lessons:
                    v = lec.get("value")
                    if isinstance(v, str):
                        try:
                            import json
                            v = json.loads(v)
                        except Exception:
                            v = {}
                    if isinstance(v, dict):
                        sit_s = sanitize_chunk(v.get("situation", ""), max_len=80)
                        app_s = sanitize_chunk(v.get("approach", ""), max_len=60)
                        if sit_s or app_s:
                            parts.append(f"  - When {sit_s}: {app_s}")
        except Exception:
            pass

        recent = self.recall_recent(5, namespace=namespace)
        if recent:
            parts.append("\nRecent events:")
            for e in recent[:5]:
                content_s = sanitize_chunk(e.get("content", ""), max_len=100)
                if content_s:
                    parts.append(f"  - [{e.get('event_type', '?')}] {content_s}")

        ctx = "\n".join(parts) if parts else ""
        return ctx

    def is_potentially_ood(self, query: str, namespace: str | None = None) -> bool:
        """True if we have stored experiences but none are relevant — potential distribution shift.
        Triggers epistemic humility for out-of-distribution queries."""
        if len(query.strip()) < 50:
            return False
        where = None
        if namespace == "chat":
            where = {"session_type": "chat"}
        elif namespace == "autonomy":
            where = {"session_type": {"$in": ["chat", "autonomy"]}}
        elif namespace == "test":
            where = {"session_type": "test"}
        if _vector_disabled():
            return self._fallback_retrieval(query, top_k, namespace)
        try:
            raw = self.vector.search(query, top_k=10, where=where)
        except Exception:
            return False
        if not raw:
            return False
        now = datetime.now()
        for r in raw:
            dist = r.get("distance", 1.0)
            meta = r.get("metadata") or {}
            imp = float(meta.get("importance", 0.5))
            ts = meta.get("timestamp", "")
            recency = 0.5
            if ts:
                try:
                    from datetime import date
                    stored = datetime.strptime(ts[:10], "%Y-%m-%d").date()
                    delta = (now.date() - stored).days
                    recency = 1.0 / (1.0 + max(0, delta) / 7)
                except Exception:
                    pass
            semantic = 1.0 - min(1.0, dist / 2.0)
            total = (
                RETRIEVAL_WEIGHTS["semantic"] * semantic
                + RETRIEVAL_WEIGHTS["importance"] * imp
                + RETRIEVAL_WEIGHTS["recency"] * recency
            )
            if total >= MIN_RETRIEVAL_SCORE:
                return False
        return True
