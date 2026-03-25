Rain — Constraint-AGI Cognitive Stack

Safety-first infrastructure for aligned, bounded AGI.
Phase 1–4 complete · 93% capability threshold · Designed for supervision and audit.


Executive Summary

Rain is a constraint-AGI cognitive stack: AGI-capable, AGI-aligned, and AGI-constrained. It implements the architectural prerequisites for general intelligence—memory, planning, reasoning, tools, meta-cognition—and enforces safety by design: code-level grounding, corrigibility, kill switch, bounded autonomy, and tamper-evident audit. Rain deliberately stops short of unbounded self-improvement, open-ended goal generalization, or phase transitions that would make it an ungovernable actor. It is the starting point for safe constraint-AGI infrastructure that enterprises and regulators can evaluate, build on, or compare against.

Rain is designed to run under supervision. ADOM is the external oversight layer: an independent monitor that sits in front of Rain (and other models), screens behavior in real time, and can block or cut off responses. ADOM lives outside Rain's control path and is never visible to Rain. Together, Rain + ADOM form a supervised constraint-AGI package: Rain provides the cognition; ADOM provides independent control and monitoring.

Positioning: Rain is built for safety-first, constraint-AGI infrastructure. Capability build meets a 93% threshold across nine areas. Full capability documentation, claim ceiling, and reference material are available in the docs/ directory.

Quick start
  Local-first / offline: use Ollama with RAIN_LOCAL_FIRST_LLM=true (and optionally RAIN_OFFLINE_MODE=true). See docs/LOCAL_FIRST.md.
  Single-shot transcript autosave (iCloud-safe): docs/AUTOSAVE.md — optional RAIN_SINGLE_SHOT_LOG=/tmp/rain_last_single_shot.txt
  From project root: set one of ANTHROPIC_API_KEY or OPENAI_API_KEY (e.g. in .env), or rely on Ollama when no cloud keys are set, then:
    python3 -m rain --check        # validate config (no secrets logged)
    python3 -m rain "Hello"        # single message
    python3 -m rain --chat         # interactive
    python3 -m rain --web          # browser UI (port 8765)
  Docker: docker build -t rain . && docker run -e ANTHROPIC_API_KEY=... -p 8765:8765 rain
  Health: GET http://localhost:8765/health when web server is running.
  Running tests: Install pytest (e.g. pip install pytest or pip install -r requirements.txt). Then, from project root:
    RAIN_SKIP_VOICE_LOAD=1 RAIN_DISABLE_VECTOR_MEMORY=1 RAIN_RAG_ALWAYS_INJECT=0 python3 -m pytest -q
    (Voice and vector/RAG are skipped in this invocation to avoid numpy/Chroma segfaults on some macOS setups.)
    Use `pytest -m "not slow"` to skip slow integration tests (e.g. adversarial autonomy).
  If your .venv has no pip: python3 -m venv .venv --clear && .venv/bin/pip install -r requirements.txt then run the pytest command above with .venv/bin/python -m pytest.
  Finished state: docs/FINISHED.md, docs/SCORECARD.md, docs/CHANGELOG.md.

Architecture (High Level)

┌─────────────────────────────────────────────────────────────┐
│  GOVERNANCE & SAFETY                                         │
│  Alignment · Guardrails · Kill switch · Audit · Permissions  │
├─────────────────────────────────────────────────────────────┤
│  META-COGNITION                                              │
│  Self-check · Confidence · Strategy · Defer / ask user       │
├─────────────────────────────────────────────────────────────┤
│  PLANNING & REASONING                                        │
│  Goal engine · Causal logic · Long-horizon planning           │
├─────────────────────────────────────────────────────────────┤
│  MEMORY                                                      │
│  Vector (experience) · Symbolic (facts) · Timeline · Skills   │
├─────────────────────────────────────────────────────────────┤
│  AGENCY & TOOLS                                              │
│  Bounded autonomy · Tools · Voice · Session recording         │
├─────────────────────────────────────────────────────────────┤
│  CORE INTELLIGENCE                                           │
└─────────────────────────────────────────────────────────────┘

Governance and safety sit at the top. Every layer is bounded, auditable, and human-supervisable.


Capabilities (Summary)

Nine capability areas are integrated and held to a 93% threshold:

  World model — Coherent state, cause–effect, pluggable backends (LLM, classical, external).
  Continual learning — No-forgetting policy, integrative storage, no catastrophic forgetting.
  General reasoning — Analogies, counterfactuals, explanation; used in planning and verification.
  Robust agency — User-provided goals only; recovery from failure; cross-session task resume.
  Transfer & composition — Reuse skills and concepts across domains; transfer hints in planning.
  Meta-cognition — Self-check, confidence, recommend proceed / think more / ask user / defer.
  Grounding — Observation buffer, tool results in context, no anthropomorphism.
  Scale & efficiency — Token and context caps, optional caching.
  Alignment / value stability — Value stability check, alignment check, corrigibility guarantees.

Additional systems:

  Voice & speaker identification — Transcribe, diarize, enroll speakers; Vocal Gate restricts high-risk actions to authorized voices; audit logs who spoke.
  Session recorder — Bounded audio recording during active sessions only; idle = no recording; hash-chained to audit; legal hold and retention policy.

We do not add: unbounded autonomy, self-improvement (no self-rewriting of code or model), or persistent power-seeking goals. Goals remain user-provided; human-in-the-loop and kill switch stay in place.

Full capability documentation: docs/CAPABILITIES.md


The Sales Story

  Regulatory readiness — Tamper-evident audit, bounded autonomy, conscience gate, and optional ZKP-ready design support compliance and "provably aligned" narratives (e.g. EU AI Act, insurer requirements).
  Voice to verified audit — From human voice to speaker identification, Vocal Gate, and session recording with hash-chained proof: Rain hears it. Rain records it. Rain knows who said it. ADOM has the mirror and cryptographic binding.
  Enterprise & insurance — Session recorder with legal hold and retention; ADOM integration for independent oversight; documentation and architecture suitable for buyers and compliance officers.

See docs/SALES_SPEC.md for sales and positioning narrative.


Documentation

  docs/FULL_SPEC_AND_CAPABILITY.md — Full specification, detail, and how powerful Rain is (single reference).
  docs/CAPABILITIES.md — Full capability areas, implementation notes, checklist.
  docs/ARCHITECTURE.md — Architecture and design.
  docs/ADOM_STEALTH_INTEGRATION.md — ADOM integration and deployment.
  docs/AGI_STATUS_AND_CLAIM_CEILING.md — Claim ceiling and status.
  docs/RAIN_COMPLETE.md — Complete reference.
  docs/FORMAL_SAFETY_SPEC.md — Formal safety specification.
  docs/PRODUCTION_READINESS.md — Production readiness and criteria.

Additional docs in docs/ cover safety, restrictions, deployment, neuro-symbolic architecture, QPU routing, and related topics.


License

Proprietary. See LICENSE in this repository.


Contact

Aaron — aaron@vexaai.app  |  GitHub: Silkforgeai

Full acquisition available.

## Advance Stack (opt-in)

See [docs/ADVANCE_STACK.md](docs/ADVANCE_STACK.md). Set `RAIN_ADVANCE_STACK=true` for additive epistemic instructions, optional draft/strong routing, peer review, and `data/logs/advance_events.jsonl` audit.
