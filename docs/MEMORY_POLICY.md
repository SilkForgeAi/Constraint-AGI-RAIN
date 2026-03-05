Rain Memory Policy

Defines what persists, what doesn't, and how memory can be revised or forgotten.

What Persists

| Type | Storage | When |
|------|---------|------|
| Experiences | Vector (ChromaDB) + Timeline | When `use_memory=True` and exchange passes `should_store()` |
| Facts | Symbolic (SQLite) | When Rain uses `remember` tool with explicit content |
| Events | Timeline (SQLite) | Every experience, fact, forgotten event |

What Does NOT Persist

- Safety-blocked prompts or responses (`[Safety] ... blocked`)
- Very short content (< 20 chars) — trivial chit-chat
- Empty or whitespace-only content
- Content with `do_not_store: true` in metadata
- Session history — in-memory only, truncated to last 20 messages; not in long-term memory unless `--memory` is used

Safe Revision & Forgetting

Forget experience (vector)
```python
memory.forget_experience(vector_id)  # Deletes from vector, logs to timeline
```

Forget fact (symbolic)
```python
memory.forget_fact(key, kind=None)  # Deletes fact, logs to timeline
```

Revise fact
Symbolic facts are revised by re-setting: `memory.remember_fact(key, new_value)` overwrites.

Audit trail
Every forget operation is logged to the timeline (`forgotten`, `fact_forgotten`) so there is an audit trail.

Importance & Retrieval (10/10)

- Importance scoring: Each exchange scored 0–1 (heuristic: length, substantive signals). Stored only if ≥ 0.35.
- Weighted retrieval: Combines semantic similarity + importance + recency for ranking.
- Contradiction detection: On store, checks similar memories for conflicts; metadata marks contradictions.
- Skills: `remember_skill(procedure)` stores procedural knowledge; `recall_skills(query)` retrieves.

Retention (Future)

- `MAX_VECTOR_EXPERIENCES` — cap vector store size
- TTL — expire experiences older than N days
