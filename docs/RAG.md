# RAG (retrieval) in Rain

## Purpose

Ground answers in documents you add to the vector store so the model can cite or rely on your material instead of inventing details.

## Ingestion

- Use the **add_document** / RAG tools from the agent when `RAIN_RAG_ENABLED=true` (default).
- Documents live under the configured vector DB path (`data/vector_db` by default). See `rain/config.py` for `RAIN_RAG_*` flags (`RAG_TOP_K`, `RAG_ALWAYS_INJECT`, etc.).

## Operations

- If Chroma or numpy causes crashes on your platform, set `RAIN_DISABLE_VECTOR_MEMORY=true` and use timeline/keyword fallbacks only.
- For production, pin dependency versions and monitor embedding API usage if using remote embedders.

## Citations

System prompts may include instructions to cite memory snippets when `Memory:` context is injected; tune prompts in the agent / grounding modules if you need stricter citation format.
