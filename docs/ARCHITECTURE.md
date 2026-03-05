Rain Architecture

AGI Cognitive Stack — Phase 1 implementation.

Stack Overview

```
┌──────────────────────── GOVERNANCE & SAFETY ────────────────────────┐
│ Alignment | Guardrails | Kill Switches | Audits | Permissions       │
└─────────────────────────────────────────────────────────────────────┘
┌──────────────────────── META-COGNITION LAYER ───────────────────────┐
│ Self-check | Bias detect | Confidence | Strategy optimizer          │
└─────────────────────────────────────────────────────────────────────┘
┌──────────────────────── PLANNING & REASONING ───────────────────────┐
│ Goal engine | Causal logic | Long-horizon planning | Tradeoffs      │
└─────────────────────────────────────────────────────────────────────┘
┌──────────────────────── MEMORY SYSTEM ──────────────────────────────┐
│ Vector (experience) | Symbolic (facts) | Timeline (events) | Skills │
└─────────────────────────────────────────────────────────────────────┘
┌──────────────────────── AGENCY & TOOLS ─────────────────────────────┐
│ calc | time | remember | (extensible)                               │
└─────────────────────────────────────────────────────────────────────┘
                              CORE (LLM)
```

Modules

| Module | Purpose |
|--------|---------|
| `rain/core/engine.py` | LLM abstraction — OpenAI, Anthropic, Ollama |
| `rain/memory/store.py` | Unified memory — vector, symbolic, timeline |
| `rain/memory/vector_memory.py` | ChromaDB + SentenceTransformer (lazy) |
| `rain/memory/symbolic_memory.py` | SQLite facts |
| `rain/memory/timeline_memory.py` | SQLite event log |
| `rain/agency/tools.py` | Tool registry, calc, time, remember |
| `rain/agency/runner.py` | Agentic loop — parse tool calls, execute, loop |
| `rain/grounding.py` | Personality substrate, anthropomorphism governor |
| `rain/planning/planner.py` | Goal → steps decomposition |
| `rain/safety/vault.py` | Hard locks, kill switch, content filter |
| `rain/governance/audit.py` | Action logging |
| `rain/meta/metacog.py` | Self-evaluation (stub) |
| `rain/chat_export.py` | Export sessions to markdown |
| `rain/progress.py` | AGI milestone tracker |

Data Layout

```
data/
├── conversations/     # Exported chat sessions (chat_export)
├── vector/            # ChromaDB embeddings
├── symbolic.db        # Facts
├── timeline.db        # Events
└── audit.log          # Governance log
```

LLM Providers

- Anthropic (Claude) (default when ANTHROPIC_API_KEY set): `ANTHROPIC_API_KEY=sk-ant-...`
- OpenAI: `OPENAI_API_KEY`, `RAIN_LLM_PROVIDER=openai`
- Ollama (default when no API keys): local, free. `ollama pull llama3.2`

Chat Modes

| Mode | Command | Memory | Tools | Export |
|------|---------|--------|-------|--------|
| Single | `run.py "msg"` | off | off | — |
| Single + tools | `run.py --tools "msg"` | off | on | — |
| Chat | `run.py --chat` | session | off | auto on bye |
| Chat + tools | `run.py --chat --tools` | session | on | auto on bye |
| Chat + memory | `run.py --chat --memory` | long-term | off | auto on bye |
| Web | `run.py --web` | session | off | — |
| Web + memory/tools | `run.py --web` + checkboxes | opt-in | opt-in | — |

Session memory = in-memory history (last 10 exchanges). Long-term memory = ChromaDB (not default in chat).

Tool Call Format

LLM outputs:
```
```tool
{"tool": "calc", "expression": "127 * 384"}
```
```

Parser also accepts raw JSON and tolerates trailing commas.

Phase Roadmap

1. Phase 1 (complete): Core + memory + tools + safety + chat + web + autonomy + Prime validation
2. Phase 2 (complete): Planning safety filter, escalation, hallucination flag
3. Phase 3 (complete): Code exec, beliefs, tool chains
4. Phase 4 (complete): Alignment and verification (capability gating, drift detection)
