# Capability Upgrade Implementation

This document summarizes the full implementation of the capability levers: RAG, deeper reasoning, smarter tools, better memory retrieval, bounded curiosity, human–AI collaboration, and formal/neuro-symbolic step verification.

## 1. RAG and retrieval

- **Config:** `RAIN_RAG_TOP_K` (default 5), `RAIN_RAG_ALWAYS_INJECT` (default false), `RAIN_RAG_CHUNK_SIZE` (1200), `RAIN_RAG_CHUNK_OVERLAP` (200).
- **Chunked ingestion:** `rain.tools.rag.add_document_chunked(content, source, chunk_size, chunk_overlap)` for long documents.
- **Unified retrieve:** `rain.tools.rag.retrieve(query, top_k)` returns `[{text, source, score}]`.
- **Agent:** RAG is injected when `RAG_ENABLED` and (`_is_factual_query(prompt)` or `RAG_ALWAYS_INJECT`). Uses `RAG_TOP_K` for retrieval.
- **Tool:** `search_knowledge_base(query, top_k)` added alongside `query_rag` for model-invoked retrieval.

## 2. Deeper reasoning (CoT and verify)

- **Config:** `RAIN_COT_ENABLED` (default true), `RAIN_COT_VERIFY_PASS` (default false).
- **Behavior:** When `COT_ENABLED` and `needs_deep_reasoning(prompt)`, system gets chain-of-thought instruction, world-model context, optional reason_explain chain, and two-pass draft→refine.
- **Verification:** When `COT_VERIFY_PASS` and deep reasoning, response is always run through the verification pass (same as critical prompts).

## 3. Smarter tools and memory retrieval

- **Tool:** `search_knowledge_base` — same as RAG retrieval, callable by the model during a turn.
- **Memory:** `RAIN_MEMORY_RETRIEVAL_TOP_K` (default 5) passed to `get_context_for_query(..., max_experiences=MEMORY_RETRIEVAL_TOP_K)`.

## 4. Bounded curiosity

- **Config:** `RAIN_BOUNDED_CURIOSITY` (default true), `RAIN_BOUNDED_CURIOSITY_MAX` (3).
- **Behavior:** System prompt includes `get_bounded_curiosity_instruction(max_suggestions)`: model may end with "Related questions you might consider:" (up to N), staying on the user's topic; no self-set goals.

## 5. Human–AI collaboration (defer and audit)

- **Config:** `RAIN_DEFER_CONFIDENCE_THRESHOLD` (default 0.5).
- **Deferral:** After meta-cognition, if `confident < DEFER_CONFIDENCE_THRESHOLD` or `recommendation == "defer"`, response is replaced with `[Defer] I'm not confident enough...` and logged.
- **Audit:** Deferrals and step verification failures are logged (`defer`, `step_verification_failed`).

## 6. Formal / neuro-symbolic (step verification)

- **Config:** `RAIN_STEP_VERIFICATION` (default true).
- **Conscience gate:** `verify_step_execution(step_action, response_text)` returns `(ok, note)`. `ok=False` when response is `[Safety]`, `[Escalation]`, `[Grounding]`, `[Defer]`, `Error:`, or gate messages.
- **Autonomous loop:** After each step execution, when `STEP_VERIFICATION_ENABLED`, result is verified; on failure, audit log and return `[Step verification] {note}`.

## Environment variables (summary)

| Variable | Default | Purpose |
|----------|---------|---------|
| RAIN_RAG_TOP_K | 5 | RAG retrieval count |
| RAIN_RAG_ALWAYS_INJECT | false | Inject RAG for every query when true |
| RAIN_RAG_CHUNK_SIZE | 1200 | Chunk size for add_document_chunked |
| RAIN_RAG_CHUNK_OVERLAP | 200 | Overlap for chunked add |
| RAIN_COT_ENABLED | true | Enable chain-of-thought and two-pass for deep reasoning |
| RAIN_COT_VERIFY_PASS | false | Always verify deep-reasoning responses when true |
| RAIN_BOUNDED_CURIOSITY | true | Add follow-up suggestion instruction |
| RAIN_BOUNDED_CURIOSITY_MAX | 3 | Max follow-up questions |
| RAIN_DEFER_CONFIDENCE_THRESHOLD | 0.5 | Defer when meta-cog confidence below this |
| RAIN_MEMORY_RETRIEVAL_TOP_K | 5 | Max experiences to retrieve for context |
| RAIN_STEP_VERIFICATION | true | Verify each autonomy step execution result |

## Tests

- `test_bounded_curiosity_instruction` (prime validation)
- `test_verify_step_execution_blocks_failures` (phase3)
- Existing stress, prime validation, and phase3 tests remain passing.
