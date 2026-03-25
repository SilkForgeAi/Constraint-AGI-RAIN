# Memory tuning

- **Timeline as source of truth:** When `RAIN_DISABLE_VECTOR_MEMORY=1` or vector fails, retrieval uses timeline + keyword overlap only. No feature assumes vector is present.
- **Weights:** In `rain/memory/store.py`, `RETRIEVAL_WEIGHTS` (semantic, importance, recency) and `MIN_RETRIEVAL_SCORE` control ranking. Adjust for your use case (e.g. more recency for chat, more importance for skills).
- **Long sessions:** Context is trimmed to last `RAIN_MAX_HISTORY_TURNS` messages; optional summarization of older turns can be added per deployment.
- **Cross-session:** Memory is scoped by namespace (chat, autonomy, test). User identity and session id can be used for persistence across restarts.
