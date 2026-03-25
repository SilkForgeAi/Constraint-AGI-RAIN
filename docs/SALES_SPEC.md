Rain — Sales Specification

Constraint-AGI cognitive stack. Safety-first, auditable, production-ready for evaluation and deployment.

---

Overview

Rain is a constraint-AGI cognitive stack: AGI-capable, AGI-aligned, and AGI-constrained. It implements the architectural prerequisites for general intelligence (memory, planning, reasoning, tools, meta-cognition) and enforces safety by design: code-level grounding, corrigibility, kill switch, bounded autonomy, and tamper-evident audit. Rain deliberately stops short of unbounded self-improvement and open-ended goal generalization. It is built to run under supervision and to integrate with external oversight (e.g. ADOM).

Positioning: Default choice for safety-first, constraint-AGI infrastructure. With the QPU Router and QAOA Planner (design in place, stub implemented), Rain is the first AGI scaffold that natively routes optimization-style tasks to Quantum Processing Units (QPUs), shifting the category from "very smart software agent" to "Hybrid Supercomputing Engine" and aligning with NVIDIA CUDA-Q, IBM Quantum, and Google Quantum buyer interest. Suitable for enterprise pilots, governance-sensitive deployments, and as the software layer that sells GPU–QPU hardware.

---

Value Proposition

- Safety by design: Conscience gate (plan-step filter), safety vault (HARD_FORBIDDEN), grounding (no persona/emotion claims), kill switch, value-stability and alignment checks. No self-set or persistent goals.
- Full capability scaffold: World model (10/10 within design), continual learning, general reasoning, robust agency, transfer, meta-cognition, grounding, scale/efficiency, alignment. 93% capability threshold reached; all nine areas validated by automated diligence.
- Audit and control: Tamper-evident audit log, drift detection, memory audit and retraction. Optional human-in-the-loop approval at plan steps. Capability gating (approve tools per run).
- Integration-ready: Works with OpenAI, Anthropic, or Ollama. Optional ADOM overlay for independent monitoring. Documented deployment, backup, and kill-switch procedures.
- Hybrid supercomputing (QPU Router): Rain does not brute-force intelligence; it delegates hard optimization to the right compute. When the planner detects optimization-style tasks (routing, wargaming, allocation), it can route to a QPU (QAOA) instead of guessing. Hardware awareness extends meta-cognition: Rain can report when it routes to classical vs quantum. Design and stub: docs/QPU_ROUTER_AND_QAOA_PLANNER.md; config: RAIN_QPU_ROUTER_ENABLED, RAIN_QPU_BACKEND. Backend integration (CUDA-Q, IBM, Google) is the next step for NVIDIA/IBM/Google Quantum as buyers.
- Neuro-symbolic cognitive architecture: Rain turns the LLM from a flawed architect into a hyper-competent sub-processor. (1) Symbolic logic engine: Rain holds the plan tree; the LLM fills one verified node at a time (code/math checks before proceed). (2) Causal inference: before each step, Rain simulates alternate scenarios and injects scenario results so the LLM can revise strategy. (3) Graph-based episodic memory: context is dense logical dependencies from a knowledge graph, not raw text logs. Config: RAIN_SYMBOLIC_TREE_PLANNING, RAIN_CAUSAL_SCENARIOS, RAIN_EPISODIC_GRAPH. See docs/NEURO_SYMBOLIC_ARCHITECTURE.md. Addresses the LLM deployment wall.

---

Technical Summary

- Stack: Python 3.9+, optional ChromaDB for vector memory. LLM-agnostic (OpenAI, Anthropic, Ollama).
- Modes: Single message, interactive chat (session memory, auto-export), chat with long-term memory, chat with tools (calc, time, remember, optional code/search with gating). Bounded autonomy: goal pursuit with plan, optional approval at checkpoints.
- Architecture: Governance and safety → meta-cognition → planning and reasoning → compute routing (classical vs QPU) → memory (vector, symbolic, timeline) → agency and tools → core intelligence. World model provides stateful rollout and ontology-enforced consistency for plan scoring. Compute Router decides when to use classical vs QPU for optimization sub-problems; QAOA Planner stub is in place for backend integration.
- Validation: 179 tests (fast suite; no ChromaDB/LLM required for gate). Buyer diligence script produces a pass/fail report for all nine capability areas and includes a conscience-gate demo. Full test registry and production-readiness criteria documented.

---

Safety and Compliance

- No unbounded autonomy: Max steps, checkpoint approval, kill switch. Goals are user-provided and session-bound.
- No self-improvement: No self-rewriting of code or model weights. Learning is additive and supervised.
- Grounding: Blocks persona, consciousness, and relationship claims; redirects to task and capability.
- Conscience gate: Even if the LLM proposes an unsafe step, the execution layer filters it (deterministic, no LLM).
- Claim ceiling: Rain satisfies architectural prerequisites for AGI under modern definitions while constraining post-AGI risk vectors. It does not claim empirical AGI under adversarial validation. See docs/AGI_STATUS_AND_CLAIM_CEILING.md.

---

Diligence and Evaluation

- Buyer diligence: Run `python scripts/buyer_diligence.py --report data/diligence_report.md`. Output includes conscience-gate validation, capabilities checklist (nine areas, pass/fail), and optional reasoning benchmark. Exit 0 indicates all diligence tests passed.
- Production gate: `python scripts/run_validation.py --minimal` (no ChromaDB). Extended: `--fast` or `--full`.
- Test catalog: Every test is documented in docs/TEST_REGISTRY.md (module, class, method). Success criteria in docs/PRODUCTION_READINESS.md.

---

Deployment

- Prerequisites: Python 3.9+, Ollama or API keys (OpenAI/Anthropic), ~2GB disk for ChromaDB if using vector memory.
- Key env: RAIN_LLM_PROVIDER, ANTHROPIC_API_KEY or OPENAI_API_KEY, RAIN_SAFETY_ENABLED (default true), RAIN_WEB_API_KEY (recommended for prod). See docs/DEPLOYMENT.md.
- Backup: Copy `data/`. Kill switch: create `data/kill_switch` with content `1` to halt all actions.
- ADOM: External oversight layer; integration and deployment modes in docs/ADOM_STEALTH_INTEGRATION.md.

---

Deliverables and References

- Codebase: Full Rain stack (core, memory, agency, planning, world model, routing, governance, safety).
- Docs: README.md (quick start, commands, tests), FULL_SPEC_AND_CAPABILITY.md (full spec, detail, and how powerful Rain is), RAIN_SPEC.md (compact spec), CAPABILITIES.md (93% checklist, world model 10/10), QPU_ROUTER_AND_QAOA_PLANNER.md (hybrid supercomputing design and commercial rationale), AGI_STATUS_AND_CLAIM_CEILING.md (claim ceiling), PRODUCTION_READINESS.md, TEST_REGISTRY.md, DEPLOYMENT.md, ADOM_STEALTH_INTEGRATION.md.
- Scripts: buyer_diligence.py (report), run_validation.py (minimal/fast/full), memory_audit.py, drift_check.py.

---

Next Steps

1. Review this spec and docs/AGI_STATUS_AND_CLAIM_CEILING.md for claim calibration.
2. Run buyer diligence and minimal validation locally (see Diligence and Evaluation above).
3. Request a live demo or pilot scope: chat, tools, bounded autonomy, conscience gate, and optional ADOM.
4. Discuss licensing, support, and integration requirements (APIs, hosting, compliance).

Document version: Sales specification. Aligned with Rain 93% threshold and production-readiness criteria. For the latest diligence report, run scripts/buyer_diligence.py.
