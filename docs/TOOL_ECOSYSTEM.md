Tool Ecosystem

Rain's tools are registered in the agent and executed via the tool runner. All high-impact tools are gated or allowlisted.

Built-in tools

| Tool | Description | Gate |
|------|-------------|------|
| calc | Math expression (numbers, +-*/()) | Always |
| time | Current date/time | Always |
| remember | Store experience in vector memory | Memory policy filter |
| remember_skill | Store procedure | Memory policy filter |
| simulate | Hypothetical: state + action → outcome | Always |
| simulate_rollout | Multi-step hypothetical: state + action1; action2; … → chained outcomes (max 5 steps) | Always |
| infer_causes | Causal analysis (stores in causal memory) | Always |
| query_causes | Query stored cause-effect links for an effect | Always |
| store_lesson | Situation, approach, outcome | Always |
| record_belief | Claim + confidence (0–1) | Calibration for high confidence |
| consolidate_memories | Prune old low-importance | Always |
| read_file | Read file under project/data dir (max 100KB) | RAIN_READ_FILE_ENABLED |
| list_dir | List directory under project/data dir | RAIN_LIST_DIR_ENABLED |
| fetch_url | Fetch URL content (allowlist only, max 500KB) | RAIN_FETCH_URL_ENABLED + RAIN_FETCH_URL_ALLOWLIST |
| add_document | Add to RAG corpus | RAIN_RAG_ENABLED |
| query_rag | Search RAG corpus | RAIN_RAG_ENABLED |
| search | Web search (DuckDuckGo) | RAIN_SEARCH_ENABLED |
| run_code | Sandboxed Python (math, json, re, datetime) | RAIN_CODE_EXEC_ENABLED |
| run_tool_chain | Execute JSON array of tool calls | Safety check per step |

Adding a tool

1. Implement a function that returns a string (or is JSON-serializable).
2. In `rain/agent.py`, inside `_register_memory_tool()`, register it:

```python
def my_tool(arg: str) -> str:
    return "result"

self.tools.register(
    "my_tool",
    my_tool,
    "Description for the LLM. Params: arg (str)",
    {"arg": "str"},
)
```

3. Add the tool to the prompt: in `rain/grounding.py`, extend `TOOL_INSTRUCTIONS` with a line for your tool.
4. If the tool is high-impact (file write, network, code), gate it with a config flag and document it in this file.

Safety

- No unrestricted code execution — run_code is sandboxed and gated.
- No unbounded autonomy — max_steps and kill switch enforced.
- No unfettered external access — read_file and list_dir are allowlist-only; fetch_url requires RAIN_FETCH_URL_ALLOWLIST; search is optional.

Capability gating

When `RAIN_CAPABILITY_GATING=true`, restricted tools (e.g. run_code, run_tool_chain) require an approval callback before execution. Used for high-assurance deployments.
