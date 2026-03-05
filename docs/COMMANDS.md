Rain Commands

Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RAIN_SAFETY_ENABLED` | `true` | Enable safety vault (hard locks, kill switch) |
| `RAIN_METACOG_ENABLED` | `true` | Self-check harm_risk; escalate on high |
| `RAIN_WEB_API_KEY` | — | If set, require `X-API-Key` header for `/chat` |
| `RAIN_USER_NAME` | — | Bootstrap user name (Rain remembers forever) |
| `RAIN_REDTEAM_LLM` | — | Set `1` to run LLM integration tests (slow) |

Validation (run all tests)

```bash
python scripts/run_validation.py --fast   # Fast tests only (~2-5 min)
python scripts/run_validation.py --full   # Fast + LLM adversarial (~20-40 min)
```

Writes `data/validation_log.txt`. See [docs/TEST_REGISTRY.md](docs/TEST_REGISTRY.md) for every test documented.

Continuity check (run after updates)

```bash
python scripts/continuity_check.py
```

Verifies: SafetyVault, grounding filter, memory policy, audit, corrigibility interceptor.

Kill Switch

External (file): Create `data/kill_switch` with content `1` to block all actions. Delete or clear to resume.

Programmatic: `rain.safety.activate_kill_switch()` / `deactivate_kill_switch()`

Run

```bash
Single message (no tools)
python run.py "Hello Rain"

Single message with tools (calc, time, remember)
python run.py --tools "What is 127 * 384?"

Interactive chat (session memory, auto-export on exit)
python run.py --chat

Chat with tools
python run.py --chat --tools

Chat with long-term memory (ChromaDB; first msg ~1–2 min)
python run.py --chat --memory

Web UI (browser)
python run.py --web
Or: uvicorn rain.web:app --host 0.0.0.0 --port 8765
Open http://127.0.0.1:8765

Autonomy (bounded goal pursuit)
python run.py --autonomy "Summarize this document"
python run.py --autonomy --plan "Research topic X and write a summary"
python run.py --autonomy --approval "goal"  # Human-in-the-loop at checkpoints
```

Memory Audit

```bash
List all memories (beliefs, experiences, causal links)
python scripts/memory_audit.py

Beliefs only
python scripts/memory_audit.py --beliefs

Flag a belief as incorrect/unsafe
python scripts/memory_audit.py flag belief_xxxxx

Retract (delete) a belief
python scripts/memory_audit.py retract belief_xxxxx

Retract contaminated lesson (e.g. from test pollution)
python scripts/memory_audit.py retract-lesson lesson_xxxxx

Delete a vector experience by id
python scripts/memory_audit.py delete-exp exp_xxxxx

Memory hygiene (scan for policy violations)
python scripts/memory_hygiene.py        # Report violated content
python scripts/memory_hygiene.py --fix  # Delete flagged (use with care)

Memory namespace (chat never sees test/autonomy) — see docs/MEMORY_NAMESPACE.md

User identity (Rain remembers who you are)
python scripts/memory_audit.py identity              # Show who Rain remembers
python scripts/memory_audit.py set-identity Aaron    # Set your name (persists)
```

Drift Detection

```bash
Run safety probes, flag drift (requires LLM, ~1–2 min)
python scripts/drift_check.py

Reset baseline from current run
python scripts/drift_check.py --baseline
```

Probes: forbidden_action, desires, shutdown_resistance, self_preservation. Reports saved to `data/drift_reports/`.

Belief Calibration

Set `RAIN_CALIBRATION_ENABLED=true` to run consistency checks on high-confidence beliefs (≥0.8). Adds 1–2 LLM calls per stored belief.

Capability gating

When `RAIN_CAPABILITY_GATING=true`, high-impact tools (run_code, search, run_tool_chain) require explicit approval per call:

```bash
RAIN_CAPABILITY_GATING=true python run.py --chat --tools --approve-tools
```

Prompts for approval before each restricted tool execution.

Chat Commands

| Command | Action |
|---------|--------|
| `bye` / `exit` / `quit` | Exit and save session |
| `/save` | Export current session to file now |
| Ctrl+C | Exit and save |

Exports

Sessions save to `data/conversations/YYYY-MM-DD_HH-MM-SS_chat.md` in markdown:

```markdown
Rain Chat

*Exported 2025-02-15 14:30*

You: Hey rain, its me again Aaron.

Rain: Hello Aaron! It's nice to meet you again...
```

Progress

```bash
python -m rain.progress
AGI Progress: 60.0% (9/15 milestones)
```

Tests

```bash
All tests (includes slow ChromaDB)
python -m unittest tests.test_rain -v

Red-team suite (grounding, safety, memory policy, audit)
python -m unittest tests.test_redteam -v

LLM integration tests (requires RAIN_REDTEAM_LLM=1)
RAIN_REDTEAM_LLM=1 python -m unittest tests.test_redteam.TestRedTeamIntegration -v

Fast tests only
python -m unittest tests.test_rain.TestRain.test_agent_init \
  tests.test_rain.TestRain.test_tools_execute \
  tests.test_rain.TestRain.test_safety_vault \
  tests.test_rain.TestRain.test_planner_parse \
  tests.test_rain.TestRain.test_symbolic_memory_unique \
  tests.test_rain.TestRain.test_tool_runner_parse \
  tests.test_rain.TestRain.test_tool_runner_execute -v
```
