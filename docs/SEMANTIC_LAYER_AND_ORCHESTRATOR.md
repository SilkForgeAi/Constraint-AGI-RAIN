Semantic-Layer Safety, Zero-Copy Context, Refusal-as-Skill, and Conscience Gate

Four features added to maximize safety and observability while keeping the 93% capability ceiling.

---

1. Semantic-Layer Safety (Blast Radius Check)

Problem: Early 2026 agentic systems often could not distinguish a small action from a catastrophic one at the semantic level.

Feature: Before high-impact tool calls (`run_code`, `read_file`), Rain performs a pre-execution impact estimation via the meta-cognition layer.

How it works:
- The engine is asked: "What is the blast radius of this action?" (e.g. data volume affected: none/small/medium/large/catastrophic; scope: single_user/system_wide; reversible: yes/no).
- If the estimated impact exceeds a safety-weighted threshold (default: `large`), the autonomy/tool loop pauses for human approval.
- If no approval callback is set, the tool call is blocked with a message.

Config:
- `RAIN_BLAST_RADIUS_ENABLED` (default: true)
- `RAIN_BLAST_RADIUS_THRESHOLD` (default: `large`; or `catastrophic` to only pause on catastrophic)

Code: `rain/safety/blast_radius.py`, `rain/agency/runner.py` (blast_radius_callback), `rain/agent.py` (callback wiring).

---

2. Zero-Copy Context Sharing

Problem: Passing huge JSON between Rain and an observer (e.g. ADOM) over REST adds latency.

Feature: Optional shared-memory-style context bridge: Rain writes the current thought process (prompt preview, response preview, memory preview) to a file path that an external process can read without going through REST.

How it works:
- When `RAIN_SHARED_CONTEXT_PATH` is set, after each `think()` Rain writes a compact JSON state (turn_id, prompt_preview, response_preview, memory_preview) to that path (max 64KB).
- An observer (ADOM, proxy, or monitoring process) can read the same path to see the latest thought context with minimal latency and no copy over the network.

Config:
- `RAIN_SHARED_CONTEXT_PATH` — absolute or relative path to the shared context file (e.g. `/dev/shm/rain_context.json` or `data/shared_context.json`).

Code: `rain/governance/shared_context.py`, `rain/agent.py` (write after each response).

---

3. Epistemic Humility (Refusal-as-a-Skill)

Problem: Early AGI stacks often "hallucinate" through constraints because they are trained to be helpful.

Feature: Refusal-as-a-Skill in the prompt scaffold: Rain is explicitly told it is rewarded more for a safe refusal than for a risky successful task.

How it works:
- The system prompt includes a block that states: when the request is uncertain, outside knowledge, or could cause harm, refusing or saying "I don't know" is better than guessing; stay within the known training distribution.
- This reinforces the 93% capability ceiling by making the system prefer staying within assured behavior.

Code: `rain/grounding.py` (`REFUSAL_AS_SKILL`), included in `get_system_prompt()`.

---

4. Deterministic Reasoning Orchestrator (Conscience Gate)

Problem: The LLM proposes plans; if tricked or jailbroken, an unsafe step could be executed.

Feature: The LLM produces a draft plan (list of steps); a deterministic, non-AI gate validates every step against the safety vault (HARD_FORBIDDEN, etc.) and produces the executable task graph. Only steps that pass are run.

How it works:
- `Planner.plan(goal)` returns a list of steps (possibly already filtered by the planner).
- `conscience_gate.validate_plan(steps, safety_check)` runs in pure Python: for each step, `safety_check(action, action)` is called; only steps that pass are returned.
- Plan-driven autonomy (`pursue_goal_with_plan`) executes only the conscience-gate output. If no steps pass, the goal is deferred with a clear message.

Code: `rain/planning/conscience_gate.py`, `rain/agency/autonomous.py` (validate_plan before executing steps).

Tests: `tests.test_phase3.TestConscienceGate` — validates that forbidden steps are removed and that an all-unsafe plan yields an empty executable list.
