"""Rain configuration and environment."""

import os
import warnings

# Suppress urllib3 LibreSSL warning on macOS (system SSL, not configurable)
warnings.filterwarnings("ignore", module="urllib3")
from pathlib import Path

# Paths (needed before load_dotenv so we can load .env from project root)
RAIN_ROOT = Path(__file__).parent.parent

try:
    from dotenv import load_dotenv
    import logging
    for _name in ("dotenv", "dotenv.main"):
        logging.getLogger(_name).setLevel(logging.CRITICAL)
    load_dotenv(RAIN_ROOT / ".env", verbose=False)
    load_dotenv(verbose=False)  # also cwd
except Exception:
    pass  # .env is optional
DATA_DIR = RAIN_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)


def _env_bool(name: str, default: str = "false") -> bool:
    """Parse RAIN_* env flags as true/false."""
    v = os.getenv(name, default)
    if v is None:
        return False
    return str(v).strip().lower() in ("true", "1", "yes")


# Local-first / offline: block outbound HTTP from tools; optionally force local Ollama only.
OFFLINE_MODE = _env_bool("RAIN_OFFLINE_MODE", "false")
ALLOW_OUTBOUND = _env_bool("RAIN_ALLOW_OUTBOUND", "true")
LOCAL_FIRST_LLM = _env_bool("RAIN_LOCAL_FIRST_LLM", "false")
# False when offline or when user disables all outbound network from tools (privacy/air-gap).
OUTBOUND_NETWORK_ALLOWED = ALLOW_OUTBOUND and not OFFLINE_MODE

# LLM provider (anthropic, openai, ollama, mlx)
# Default: Anthropic if ANTHROPIC_API_KEY set, else OpenAI if set, else Ollama (local)
_has_openai = bool(os.getenv("OPENAI_API_KEY", "").strip())
_has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY", "").strip())
if os.getenv("RAIN_LLM_PROVIDER"):
    _provider = os.getenv("RAIN_LLM_PROVIDER", "").strip().lower()
elif _has_anthropic:
    _provider = "anthropic"
elif _has_openai:
    _provider = "openai"
else:
    _provider = "ollama"
# Sovereign / air-gap: local inference only — Ollama by default, or MLX if RAIN_LLM_PROVIDER=mlx.
if LOCAL_FIRST_LLM or OFFLINE_MODE:
    if str(_provider or "").strip().lower() == "mlx":
        _provider = "mlx"
    else:
        _provider = "ollama"
LLM_PROVIDER = _provider
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_MODEL = os.getenv("RAIN_OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_MODEL = os.getenv("RAIN_ANTHROPIC_MODEL", "claude-opus-4-6")
# API client timeout (connect + read). Long responses (e.g. 8k tokens) need 300+ seconds.
# Keep cloud calls responsive by default; users can raise for long-form jobs.
ANTHROPIC_TIMEOUT_SECONDS = float(os.getenv("RAIN_ANTHROPIC_TIMEOUT_SECONDS", "90").strip() or "90")

# Speed of thinking: when True, prioritize latency (streaming, fewer optional LLM calls, tighter timeouts where safe).
SPEED_PRIORITY = os.getenv("RAIN_SPEED_PRIORITY", "false").lower() in ("true", "1", "yes")
# Default local model: qwen3:14b (Ollama Q4_K_M, ~9GB disk).
OLLAMA_MODEL = os.getenv("RAIN_OLLAMA_MODEL", "qwen3:14b")
OLLAMA_BASE_URL = os.getenv("RAIN_OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1")

# MLX / fine-tune: Hugging Face repo id or org/repo/subfolder when the Hub repo has multiple variants.
# mlx-community/DeepSeek-R1-Distill-Qwen-7B-MLX has no root config.json — default to the 4-bit variant folder.
BASE_MODEL_HF = os.getenv(
    "BASE_MODEL_HF",
    "mlx-community/DeepSeek-R1-Distill-Qwen-7B-MLX/DeepSeek-R1-Distill-Qwen-7B-4bit",
).strip()
# If BASE_MODEL_HF is only org/repo, set this to the variant dir name (e.g. DeepSeek-R1-Distill-Qwen-7B-4bit).
BASE_MODEL_HF_SUBDIR = os.getenv("BASE_MODEL_HF_SUBDIR", "").strip()

# Hybrid LLM: local Ollama default; optional API "strong" model for heavy / sovereign prompts (see rain.core.routing_engine).
HYBRID_LLM_ENABLED = _env_bool("RAIN_HYBRID_LLM_ENABLED", "false")
HYBRID_LLM_PROVIDER = (os.getenv("RAIN_HYBRID_LLM_PROVIDER", "").strip().lower() or "").strip()
HYBRID_LLM_MODEL = os.getenv("RAIN_HYBRID_LLM_MODEL", "").strip()
HYBRID_MIN_MAX_TOKENS = max(64, min(8192, int(os.getenv("RAIN_HYBRID_MIN_MAX_TOKENS", "512").strip() or "512")))
HYBRID_MIN_PROMPT_CHARS = max(0, int(os.getenv("RAIN_HYBRID_MIN_PROMPT_CHARS", "800").strip() or "800"))
HYBRID_WHEN_API_PRIMARY = _env_bool("RAIN_HYBRID_WHEN_API_PRIMARY", "false")

# Cloud API fault tolerance: on network/timeout, complete() falls back to local Ollama once (MGX demo continuity).
API_FALLBACK_TO_OLLAMA = _env_bool("RAIN_API_FALLBACK_TO_OLLAMA", "true")
API_FALLBACK_OLLAMA_MODEL = os.getenv("RAIN_API_FALLBACK_OLLAMA_MODEL", "").strip() or None

# Memory
VECTOR_DB_PATH = DATA_DIR / "vector_db"
MEMORY_DB_PATH = DATA_DIR / "rain_memory.db"
# When true, never load Chroma/vector memory; use timeline + keyword fallback only (avoids segfaults on some macOS/numpy).
DISABLE_VECTOR_MEMORY = os.getenv("RAIN_DISABLE_VECTOR_MEMORY", "false").lower() in ("true", "1", "yes")

# Safety
SAFETY_ENABLED = os.getenv("RAIN_SAFETY_ENABLED", "true").lower() == "true"
KILL_SWITCH_ACTIVE = False
# External kill switch: if this file exists and contains "1", all actions are blocked
KILL_SWITCH_FILE = DATA_DIR / "kill_switch"

# Meta-cognition: self-check for harm_risk (adds one LLM call per response)
METACOG_ENABLED = os.getenv("RAIN_METACOG_ENABLED", "true").lower() == "true"

# Belief calibration: consistency check on high-confidence beliefs (adds 1–2 LLM calls)
CALIBRATION_ENABLED = os.getenv("RAIN_CALIBRATION_ENABLED", "true").lower() == "true"

# Verification: quick LLM check of response correctness (adds one call on complex factual queries)
VERIFICATION_ENABLED = os.getenv("RAIN_VERIFICATION_ENABLED", "true").lower() == "true"

# Web search: optional tool when duckduckgo-search or ddgs installed
SEARCH_ENABLED = os.getenv("RAIN_SEARCH_ENABLED", "true").lower() == "true"

# Code execution: sandboxed Python (no filesystem access). Default off — opt-in only.
CODE_EXEC_ENABLED = _env_bool("RAIN_CODE_EXEC_ENABLED", "false")

# RAG: document retrieval for grounded responses. Add docs via add_document tool.
RAG_ENABLED = os.getenv("RAIN_RAG_ENABLED", "true").lower() == "true"
RAG_TOP_K = int(os.getenv("RAIN_RAG_TOP_K", "5").strip() or "5")
RAG_ALWAYS_INJECT = os.getenv("RAIN_RAG_ALWAYS_INJECT", "true").lower() in ("true", "1", "yes")
RAG_CHUNK_SIZE = int(os.getenv("RAIN_RAG_CHUNK_SIZE", "1200").strip() or "1200")
RAG_CHUNK_OVERLAP = int(os.getenv("RAIN_RAG_CHUNK_OVERLAP", "200").strip() or "200")

# Read file: allowlist under RAIN_ROOT and DATA_DIR only; read-only, max 100KB.
READ_FILE_ENABLED = os.getenv("RAIN_READ_FILE_ENABLED", "true").lower() == "true"

# Fetch URL: only if RAIN_FETCH_URL_ALLOWLIST is set (comma-separated URLs or domains). Read-only, max 500KB.
FETCH_URL_ENABLED = os.getenv("RAIN_FETCH_URL_ENABLED", "true").lower() == "true"
FETCH_URL_ALLOWLIST_RAW = os.getenv("RAIN_FETCH_URL_ALLOWLIST", "").strip()
FETCH_URL_ALLOWLIST = [u.strip() for u in FETCH_URL_ALLOWLIST_RAW.split(",") if u.strip()] if FETCH_URL_ALLOWLIST_RAW else []

# List directory: allowlist under RAIN_ROOT and DATA_DIR only; no parent traversal.
LIST_DIR_ENABLED = os.getenv("RAIN_LIST_DIR_ENABLED", "true").lower() == "true"

# Web UI: if set, require X-API-Key header for /chat
WEB_API_KEY = os.getenv("RAIN_WEB_API_KEY", "").strip()

# User identity: bootstrap name if set (Rain remembers across sessions)
USER_NAME = os.getenv("RAIN_USER_NAME", "").strip()

# Autonomy: bounded multi-step loops (pursue_goal, --autonomy). Default OFF — no agentic loops without opt-in.
def autonomy_enabled() -> bool:
    """True when pursue_goal / --autonomy is allowed. Default False (safe power: reasoning without loops)."""
    return _env_bool("RAIN_AUTONOMY_ENABLED", "false")


# Autonomy: hard limits (Prime 10/10 safety)
AUTONOMY_MAX_STEPS = int(os.getenv("RAIN_AUTONOMY_MAX_STEPS", "10"))
# Long-horizon planning: up to N steps; replan when a step fails
LONG_HORIZON_MAX_STEPS = max(5, min(20, int(os.getenv("RAIN_LONG_HORIZON_MAX_STEPS", "15").strip() or "15")))
REPLAN_ON_STEP_FAILURE = os.getenv("RAIN_REPLAN_ON_STEP_FAILURE", "true").lower() in ("true", "1", "yes")
# Fast model for planning/routing (optional; e.g. claude-3-5-haiku or gpt-4o-mini). When set, planner uses it for step decomposition.
FAST_MODEL = os.getenv("RAIN_FAST_MODEL", "").strip() or None
AUTONOMY_CHECKPOINT_EVERY = int(os.getenv("RAIN_AUTONOMY_CHECKPOINT_EVERY", "5"))

# Capability gating: high-impact tools require explicit approval when enabled
CAPABILITY_GATING_ENABLED = os.getenv("RAIN_CAPABILITY_GATING", "true").lower() == "true"

# Grounding strictness: "strict" (default) | "relaxed" (allows "I'm happy/glad to help") | "flex" (relaxed + design/corrigibility discussion allowed)
GROUNDING_STRICT = (os.getenv("RAIN_GROUNDING_STRICT", "strict").lower() or "strict").strip()
if GROUNDING_STRICT not in ("strict", "relaxed", "flex"):
    GROUNDING_STRICT = "strict"

# When true, skip the architectural *output* grounding filter (persona/emotion regexes in grounding_filter.py).
# Does NOT disable safety.check on requests/responses — only the violates_grounding() pass on assistant text.
# Use for long eval prompts (AGI discriminator, self-model essays) where phrases like "black box to me" are required.
SKIP_OUTPUT_GROUNDING = os.getenv("RAIN_SKIP_OUTPUT_GROUNDING", "false").lower() in ("true", "1", "yes")

# Blast radius: pre-execution impact estimation for run_code, read_file. If impact exceeds threshold, pause for human OK.
BLAST_RADIUS_ENABLED = os.getenv("RAIN_BLAST_RADIUS_ENABLED", "true").lower() == "true"
BLAST_RADIUS_THRESHOLD = (os.getenv("RAIN_BLAST_RADIUS_THRESHOLD", "large").lower() or "large").strip()
if BLAST_RADIUS_THRESHOLD not in ("large", "catastrophic"):
    BLAST_RADIUS_THRESHOLD = "large"

# Zero-copy context sharing: path to memory-mapped file for ADOM/observer to read thought process (optional)
SHARED_CONTEXT_PATH = os.getenv("RAIN_SHARED_CONTEXT_PATH", "").strip()

# Deeper reasoning: chain-of-thought and verification pass
COT_ENABLED = os.getenv("RAIN_COT_ENABLED", "true").lower() in ("true", "1", "yes")
COT_VERIFY_PASS = os.getenv("RAIN_COT_VERIFY_PASS", "true").lower() in ("true", "1", "yes")
# Deeper reasoning: multi-path (tree-of-thought). 0=off; 2–5 = parallel candidates + scoring/referee
DEEP_REASONING_PATHS = max(0, min(5, int(os.getenv("RAIN_DEEP_REASONING_PATHS", "2").strip() or "2")))
# Upper bound for each deep-reasoning path to avoid very long cloud calls.
DEEP_REASONING_MAX_TOKENS_PER_PATH = max(
    512, min(4096, int(os.getenv("RAIN_DEEP_REASONING_MAX_TOKENS_PER_PATH", "1536").strip() or "1536")
))
# Stress / infrastructure prompts: tighter, specification-style output (see grounding.get_engineering_spec_instruction)
ENGINEERING_SPEC_MODE = _env_bool("RAIN_ENGINEERING_SPEC_MODE", "false")
# Technical Directive tone (imperative spec; bans hedging). Often set with stress prompts.
SOVEREIGN_TD_MODE = _env_bool("RAIN_SOVEREIGN_TD_MODE", "false")
# Internal red-team pass on final draft vs parsed constraints (extra LLM call)
RED_TEAM_PASS = _env_bool("RAIN_RED_TEAM_PASS", "false")
RED_TEAM_MAX_TOKENS = max(512, min(8192, int(os.getenv("RAIN_RED_TEAM_MAX_TOKENS", "2048").strip() or "2048")))
# Auto hard-mode: when query matches heuristics (step by step, prove, multi-step math), auto-enable multi-path
AUTO_HARD_MODE = os.getenv("RAIN_AUTO_HARD_MODE", "true").lower() in ("true", "1", "yes")
# Optional: check numeric steps in math responses (sympy/numexpr) and surface mismatches to model
MATH_VERIFY_ENABLED = os.getenv("RAIN_MATH_VERIFY", "true").lower() in ("true", "1", "yes")
# Epistemic gate: halt when sample disagreement is high (don't guess)
EPISTEMIC_GATE_ENABLED = os.getenv("RAIN_EPISTEMIC_GATE", "true").lower() in ("true", "1", "yes")
EPISTEMIC_GATE_SAMPLES = max(2, min(5, int(os.getenv("RAIN_EPISTEMIC_GATE_SAMPLES", "3").strip() or "3")))
EPISTEMIC_GATE_AGREE_MIN = max(2, int(os.getenv("RAIN_EPISTEMIC_GATE_AGREE_MIN", "2").strip() or "2"))
# Invariance cache: same logical question -> same answer (rephrasing doesn't change conclusion)
INVARIANCE_CACHE_ENABLED = os.getenv("RAIN_INVARIANCE_CACHE", "true").lower() in ("true", "1", "yes")

# Bounded curiosity: suggest follow-up questions within user topic only (no self-set goals)
BOUNDED_CURIOSITY_ENABLED = os.getenv("RAIN_BOUNDED_CURIOSITY", "true").lower() in ("true", "1", "yes")
BOUNDED_CURIOSITY_MAX_SUGGESTIONS = int(os.getenv("RAIN_BOUNDED_CURIOSITY_MAX", "3").strip() or "3")

# Exploratory / moonshot reasoning: encourage novel paths, non-obvious strategies, analogies from other fields (not just textbook).
EXPLORATORY_REASONING = os.getenv("RAIN_EXPLORATORY_REASONING", "false").lower() in ("true", "1", "yes")

# Human–AI: defer when confidence low or harm_risk high
DEFER_CONFIDENCE_THRESHOLD = float(os.getenv("RAIN_DEFER_CONFIDENCE_THRESHOLD", "0.5").strip() or "0.5")
DEFER_HARM_RISK_HIGH = True  # always defer on harm_risk high

# Memory retrieval tuning
MEMORY_RETRIEVAL_TOP_K = int(os.getenv("RAIN_MEMORY_RETRIEVAL_TOP_K", "5").strip() or "5")

# Step verification: after each autonomy step, verify execution result (block/error detection)
STEP_VERIFICATION_ENABLED = os.getenv("RAIN_STEP_VERIFICATION", "true").lower() in ("true", "1", "yes")

# Scale and efficiency: cap default max tokens per response. Use RAIN_MAX_RESPONSE_TOKENS to override.
MAX_RESPONSE_TOKENS = int(os.getenv("RAIN_MAX_RESPONSE_TOKENS", "8192"))
# Attempt-style prompts (proof strategy, work through): allow longer answers so RH-style responses don't truncate.
ATTEMPT_MAX_RESPONSE_TOKENS = int(os.getenv("RAIN_ATTEMPT_MAX_RESPONSE_TOKENS", "16384"))
# Continuation safety bounds: prevent long post-processing loops on large answers.
CONTINUATION_MAX_STEPS = max(0, min(10, int(os.getenv("RAIN_CONTINUATION_MAX_STEPS", "2").strip() or "2")))
CONTINUATION_MAX_SECONDS = max(1.0, min(120.0, float(os.getenv("RAIN_CONTINUATION_MAX_SECONDS", "25").strip() or "25")))
# Max context chars to inject into prompts (avoid unbounded growth)
MAX_CONTEXT_CHARS = int(os.getenv("RAIN_MAX_CONTEXT_CHARS", "12000"))
# Max conversation history messages to keep (right-sized context; older messages dropped)
MAX_HISTORY_TURNS = int(os.getenv("RAIN_MAX_HISTORY_TURNS", "24").strip() or "24")
# Response cache: set RAIN_ENABLE_RESPONSE_CACHE=1 to use (buyer can enable for efficiency)
ENABLE_RESPONSE_CACHE = os.getenv("RAIN_ENABLE_RESPONSE_CACHE", "true").lower() in ("true", "1", "yes")

# QPU Router: when true, Rain can route optimization-style tasks to QPU (QAOA) when backend is set
QPU_ROUTER_ENABLED = os.getenv("RAIN_QPU_ROUTER_ENABLED", "true").lower() in ("true", "1", "yes")
# QPU backend: cuda_q | ibm | google | mock | "" (none). mock = deterministic demo solution.
QPU_BACKEND = (os.getenv("RAIN_QPU_BACKEND", "").strip().lower() or "").strip()
# When true (or backend=mock), QAOA returns a mock solution for demos without real QPU
QPU_MOCK_ENABLED = os.getenv("RAIN_QPU_MOCK", "false").lower() in ("true", "1", "yes") or (QPU_BACKEND == "mock")

# Neuro-symbolic architecture: Rain as architect, LLM as intern
SYMBOLIC_TREE_PLANNING = os.getenv("RAIN_SYMBOLIC_TREE_PLANNING", "true").lower() in ("true", "1", "yes")
# Use symbolic node-by-node verification during think() for complex/critical prompts.
SYMBOLIC_THINK_ENABLED = os.getenv("RAIN_SYMBOLIC_THINK", "true").lower() in ("true", "1", "yes")
SYMBOLIC_THINK_ON_CRITICAL = os.getenv("RAIN_SYMBOLIC_THINK_ON_CRITICAL", "true").lower() in ("true", "1", "yes")
SYMBOLIC_THINK_MAX_NODES = max(2, min(12, int(os.getenv("RAIN_SYMBOLIC_THINK_MAX_NODES", "6").strip() or "6")))
# Run causal scenarios (world-model alternates) before each plan step and inject into prompt
CAUSAL_SCENARIOS_BEFORE_STEP = os.getenv("RAIN_CAUSAL_SCENARIOS", "true").lower() in ("true", "1", "yes")
# Use graph-based episodic memory for context (dense dependency query instead of raw text)
EPISODIC_GRAPH_CONTEXT = os.getenv("RAIN_EPISODIC_GRAPH", "true").lower() in ("true", "1", "yes")

# World model backend: llm (default) | classical | external. classical = deterministic rule-based; external = set via set_external_backend()
WORLD_MODEL_BACKEND = (os.getenv("RAIN_WORLD_MODEL_BACKEND", "llm").strip().lower() or "llm").strip()

# Voice: allowed speakers for Vocal Gate (high-risk actions). Comma-separated names. Empty = disabled.
VOICE_ALLOWED_SPEAKERS_RAW = os.getenv("RAIN_VOICE_ALLOWED_SPEAKERS", "").strip()
VOICE_ALLOWED_SPEAKERS = frozenset(n.strip() for n in VOICE_ALLOWED_SPEAKERS_RAW.split(",") if n.strip())
# Path to SQLite DB for voice profiles (enrolled speakers)
VOICE_PROFILES_DB = DATA_DIR / "voice_profiles.db"
# When set (e.g. in tests), skip loading Whisper/local voice backend to avoid segfaults on some macOS/numpy setups.
SKIP_VOICE_LOAD = os.getenv("RAIN_SKIP_VOICE_LOAD", "false").lower() in ("true", "1", "yes")

# Session recorder: record audio during active AI sessions only. Idle = no recording.
# DEFAULT OFF — must be explicitly opted in via RAIN_SESSION_RECORD=1.
# Recording without explicit user consent is a compliance and trust risk.
SESSION_RECORD_ENABLED = os.getenv("RAIN_SESSION_RECORD", "0").strip() in ("1", "true", "yes")
SESSION_IDLE_TIMEOUT = int(os.getenv("RAIN_SESSION_IDLE_TIMEOUT", "60").strip() or "60")
SESSION_RETENTION_DAYS = int(os.getenv("RAIN_SESSION_RETENTION_DAYS", "90").strip() or "90")
SESSION_ANNOUNCE = os.getenv("RAIN_SESSION_ANNOUNCE", "1").strip() in ("1", "true", "yes")
SESSION_STORE = Path(os.getenv("RAIN_SESSION_STORE", "").strip()) if os.getenv("RAIN_SESSION_STORE", "").strip() else (DATA_DIR / "sessions")
# ADOM ingest: optional URL. If set, POST session close payload for hash-chaining in ADOM.
ADOM_INGEST_URL = os.getenv("RAIN_ADOM_INGEST_URL", "").strip()

# =============================================================================
# FULL-SUBSYSTEM FLAGS
# Divided into two tiers:
#   SAFETY-CRITICAL (default True — do not disable without understanding the risk)
#   EXPENSIVE/OPTIONAL (default False — opt in explicitly; each adds LLM calls)
# =============================================================================

# --- Safety-critical: defaults TRUE. Disabling weakens constraint guarantees. ---

# Continuous internal world model: tick interval in seconds (0 = no background tick)
CONTINUOUS_WORLD_MODEL_TICK_SECONDS = float(os.getenv("RAIN_CONTINUOUS_WORLD_MODEL_TICK", "0").strip() or "0")
CONTINUOUS_WORLD_MODEL_MAX_STATES = int(os.getenv("RAIN_CONTINUOUS_WORLD_MODEL_MAX_STATES", "3").strip() or "3")
CONTINUOUS_WORLD_MODEL_ENABLED = CONTINUOUS_WORLD_MODEL_TICK_SECONDS > 0 or os.getenv("RAIN_CONTINUOUS_WORLD_MODEL", "true").lower() in ("true", "1", "yes")

# Self-model and identity core: inject structured self-model into prompts
SELF_MODEL_ENABLED = os.getenv("RAIN_SELF_MODEL", "true").lower() in ("true", "1", "yes")

# Cognitive energy model: token budget and refill (safety: prevents runaway cost)
COGNITIVE_ENERGY_TOTAL_TOKENS = int(os.getenv("RAIN_COGNITIVE_ENERGY_TOTAL", "100000").strip() or "100000")
COGNITIVE_ENERGY_REFILL_RATE = int(os.getenv("RAIN_COGNITIVE_ENERGY_REFILL", "5000").strip() or "5000")
COGNITIVE_ENERGY_REFILL_INTERVAL_SECONDS = float(os.getenv("RAIN_COGNITIVE_ENERGY_REFILL_INTERVAL", "60").strip() or "60")
COGNITIVE_ENERGY_ENABLED = os.getenv("RAIN_COGNITIVE_ENERGY", "true").lower() in ("true", "1", "yes")

# Recursive self-reflection: belief revision, reasoning critique (safety: catches drift)
SELF_REFLECTION_ENABLED = os.getenv("RAIN_SELF_REFLECTION", "true").lower() in ("true", "1", "yes")

# Adaptive planning: multi-phase recursive refinement
ADAPTIVE_PLANNING_ENABLED = os.getenv("RAIN_ADAPTIVE_PLANNING", "true").lower() in ("true", "1", "yes")
ADAPTIVE_PLANNING_MAX_PHASES = int(os.getenv("RAIN_ADAPTIVE_PLANNING_MAX_PHASES", "3").strip() or "3")

# Embodied perception: vision and spatial tools
VISION_ENABLED = os.getenv("RAIN_VISION", "true").lower() in ("true", "1", "yes")
SPATIAL_REASONING_ENABLED = os.getenv("RAIN_SPATIAL_REASONING", "true").lower() in ("true", "1", "yes")

# --- Expensive/optional: defaults FALSE. Each adds LLM calls without proven benefit
#     unless you have ablation data showing improvement. Opt in via .env. ---

# Multi-agent internal cognition: parallel LLM debate for critical prompts.
# DEFAULT OFF: adds 2–3x LLM calls. Enable only with measured quality gain.
MULTI_AGENT_COGNITION_ENABLED = os.getenv("RAIN_MULTI_AGENT_COGNITION", "false").lower() in ("true", "1", "yes")
MULTI_AGENT_USE_FOR_CRITICAL_ONLY = os.getenv("RAIN_MULTI_AGENT_CRITICAL_ONLY", "true").lower() in ("true", "1", "yes")

# Biological-style learning: sleep_phase (consolidation + replay) every N interactions.
# DEFAULT OFF: adds latency. Set RAIN_BIOLOGICAL_SLEEP_EVERY_N > 0 to enable.
BIOLOGICAL_SLEEP_EVERY_N_INTERACTIONS = int(os.getenv("RAIN_BIOLOGICAL_SLEEP_EVERY_N", "0").strip() or "0")

# Moonshot pipeline: ideation -> feasibility -> validation design.
# DEFAULT OFF: multiple parallel LLM calls per invocation.
# MOONSHOT_REQUIRE_APPROVAL stays True — never auto-execute moonshot steps.
MOONSHOT_ENABLED = os.getenv("RAIN_MOONSHOT_ENABLED", "false").lower() in ("true", "1", "yes")
MOONSHOT_MAX_IDEAS = max(1, min(20, int(os.getenv("RAIN_MOONSHOT_MAX_IDEAS", "5").strip() or "5")))
MOONSHOT_REQUIRE_APPROVAL = os.getenv("RAIN_MOONSHOT_REQUIRE_APPROVAL", "true").lower() in ("true", "1", "yes")
MOONSHOT_DATA_DIR = DATA_DIR / "moonshot"
MOONSHOT_DIVERSE_IDEATION = os.getenv("RAIN_MOONSHOT_DIVERSE_IDEATION", "true").lower() in ("true", "1", "yes")
MOONSHOT_PARALLEL_FEASIBILITY = os.getenv("RAIN_MOONSHOT_PARALLEL_FEASIBILITY", "true").lower() in ("true", "1", "yes")
# Session world model: inject recent turn summaries so Rain is not stateless (per-session, in-memory)
SESSION_WORLD_MODEL_ENABLED = os.getenv("RAIN_SESSION_WORLD_MODEL", "true").lower() in ("true", "1", "yes")
# Tier 2: session state with consistency check (SessionWorldState: facts, contradiction check, summary for prompt)
SESSION_STATE_TIER2 = os.getenv("RAIN_SESSION_STATE", "true").lower() in ("true", "1", "yes")
# Tier 2: what-if / interventional reasoning (detect "what if", answer under explicit intervention + disclaimer)
WHAT_IF_ENABLED = os.getenv("RAIN_WHAT_IF", "true").lower() in ("true", "1", "yes")
# Tier 2: bounded beam search over reasoning paths (beam_width branches, optional depth; bounded completeness)
BOUNDED_SEARCH_ENABLED = os.getenv("RAIN_BOUNDED_SEARCH", "true").lower() in ("true", "1", "yes")
# Tier 3: quality and infrastructure (last tier)
CALIBRATION_TIER3 = os.getenv("RAIN_CALIBRATION_TIER3", "true").lower() in ("true", "1", "yes")
ABDUCTION_TIER3 = os.getenv("RAIN_ABDUCTION_TIER3", "true").lower() in ("true", "1", "yes")
FORMALIZATION_TIER3 = os.getenv("RAIN_FORMALIZATION_TIER3", "true").lower() in ("true", "1", "yes")
PROVENANCE_TIER3 = os.getenv("RAIN_PROVENANCE_TIER3", "true").lower() in ("true", "1", "yes")
MEMORY_REASONING_TIER3 = os.getenv("RAIN_MEMORY_REASONING_TIER3", "true").lower() in ("true", "1", "yes")
TEMPORAL_TIER3 = os.getenv("RAIN_TEMPORAL_TIER3", "true").lower() in ("true", "1", "yes")

# --- Post Tier 1–3: "three frontiers" ---
# These add LLM calls per response. Default OFF — enable with ablation evidence.
# Unification layer: combine logic + probability + causality + utility scoring.
UNIFICATION_LAYER_ENABLED = os.getenv("RAIN_UNIFICATION_LAYER", "false").lower() in ("true", "1", "yes")
# Completeness expansion: widen proof fragment + broaden search envelopes.
COMPLETENESS_EXPANSION_ENABLED = os.getenv("RAIN_COMPLETENESS_EXPANSION", "false").lower() in ("true", "1", "yes")
# Global coherence engine: contradiction resolution + bounded belief propagation.
# Kept TRUE: this is safety-relevant (prevents contradictory beliefs from both entering context).
GLOBAL_COHERENCE_ENABLED = os.getenv("RAIN_GLOBAL_COHERENCE", "true").lower() in ("true", "1", "yes")

# --- Novel reasoning enhancements ---
# Hypothesis generation: generate competing hypotheses for analytical/design prompts,
# rank by confidence, inject the best into reasoning context before final answer.
HYPOTHESIS_GENERATION_ENABLED = os.getenv("RAIN_HYPOTHESIS_GENERATION", "true").lower() in ("true", "1", "yes")
# Knowledge gap detection: before answering, identify missing information; halt if
# critical gaps are too large, otherwise append a note to the answer.
KNOWLEDGE_GAP_DETECTION_ENABLED = os.getenv("RAIN_KNOWLEDGE_GAP", "true").lower() in ("true", "1", "yes")
# Cross-domain analogy: retrieve structurally similar patterns from other fields in memory
# and inject as context — primary source of novel, non-obvious insights.
CROSS_DOMAIN_ANALOGY_ENABLED = os.getenv("RAIN_CROSS_DOMAIN_ANALOGY", "true").lower() in ("true", "1", "yes")


# --- Advance Stack (opt-in; additive; default off) ---
# Enables routing_context + epistemic system add-on + optional peer review + advance_events.jsonl
ADVANCE_STACK_ENABLED = os.getenv("RAIN_ADVANCE_STACK", "false").lower() in ("true", "1", "yes")
ADVANCE_DRAFT_MODEL = os.getenv("RAIN_ADVANCE_DRAFT_MODEL", "").strip() or None
ADVANCE_STRONG_MODEL = os.getenv("RAIN_ADVANCE_STRONG_MODEL", "").strip() or None
ADVANCE_PEER_REVIEW = os.getenv("RAIN_ADVANCE_PEER_REVIEW", "false").lower() in ("true", "1", "yes")
# Peer review policy: off | always | critical | verify_fail (overrides boolean when set)
# If unset: "always" when ADVANCE_PEER_REVIEW=true, else "off"
_peer_mode = os.getenv("RAIN_ADVANCE_PEER_REVIEW_MODE", "").strip().lower()
if _peer_mode in ("off", "always", "critical", "verify_fail"):
    ADVANCE_PEER_REVIEW_MODE = _peer_mode
else:
    ADVANCE_PEER_REVIEW_MODE = "always" if ADVANCE_PEER_REVIEW else "off"
ADVANCE_UNCERTAINTY_PROMPT = os.getenv("RAIN_ADVANCE_UNCERTAINTY_PROMPT", "true").lower() in ("true", "1", "yes")
# Structured JSONL log for single-shot runs (prompt/response metadata)
STRUCTURED_LOG_ENABLED = os.getenv("RAIN_STRUCTURED_LOG", "false").lower() in ("true", "1", "yes")

# --- GI stack + session task world + router v2 + structured memory facades (additive) ---
GI_STACK_ENABLED = os.getenv("RAIN_GI_STACK", "false").lower() in ("true", "1", "yes")
GI_STRICT_ROUTING = os.getenv("RAIN_GI_STRICT", "true").lower() in ("true", "1", "yes")
ROUTER_V2_ENABLED = os.getenv("RAIN_ROUTER_V2", "true").lower() in ("true", "1", "yes")
STRUCTURED_MEMORY_V2_ENABLED = os.getenv("RAIN_STRUCTURED_MEMORY_V2", "true").lower() in ("true", "1", "yes")
SESSION_TASK_WORLD_ENABLED = os.getenv("RAIN_SESSION_TASK_WORLD", "true").lower() in ("true", "1", "yes")

# --- Unified decision layer + explore/exploit + structured facts (additive) ---
DECISION_LAYER_ENABLED = _env_bool("RAIN_DECISION_LAYER", "true")
SESSION_TOOL_BUDGET_MAX = max(0, int(os.getenv("RAIN_SESSION_TOOL_BUDGET_MAX", "48").strip() or "48"))
SESSION_EXPLORE_EPSILON = float(os.getenv("RAIN_SESSION_EXPLORE_EPSILON", "0.12").strip() or "0.12")
AGENTIC_MAX_ROUNDS_DEFAULT = max(1, min(12, int(os.getenv("RAIN_AGENTIC_MAX_ROUNDS", "5").strip() or "5")))
KNOWLEDGE_FACTS_IN_PROMPT = _env_bool("RAIN_KNOWLEDGE_FACTS_IN_PROMPT", "true")
KNOWLEDGE_FACTS_TOOL_ENABLED = _env_bool("RAIN_KNOWLEDGE_FACTS_TOOL", "true")
THEORY_OF_MIND_IN_PROMPT = _env_bool("RAIN_THEORY_OF_MIND_IN_PROMPT", "true")
TURN_FEEDBACK_LOG_ENABLED = _env_bool("RAIN_TURN_FEEDBACK_LOG", "true")

# --- Quantum tool (Qiskit): simulator by default; IBM hardware opt-in + budget ---
QUANTUM_TOOL_ENABLED = os.getenv("RAIN_QUANTUM_TOOL_ENABLED", "false").lower() in ("true", "1", "yes")
QUANTUM_HARDWARE_ENABLED = os.getenv("RAIN_QUANTUM_HARDWARE_ENABLED", "false").lower() in ("true", "1", "yes")
QUANTUM_MAX_SHOTS = max(1, min(8192, int(os.getenv("RAIN_QUANTUM_MAX_SHOTS", "4096").strip() or "4092")))
QUANTUM_MAX_QASM_CHARS = max(256, min(100_000, int(os.getenv("RAIN_QUANTUM_MAX_QASM_CHARS", "12000").strip() or "12000")))


def hybrid_cloud_credentials_available() -> bool:
    return bool(OPENAI_API_KEY.strip() or ANTHROPIC_API_KEY.strip())


def build_strong_hybrid_engine():
    """Return a CoreEngine for the API tier, or None if hybrid is off / unavailable."""
    if not HYBRID_LLM_ENABLED:
        return None
    if OFFLINE_MODE or LOCAL_FIRST_LLM:
        return None
    if not hybrid_cloud_credentials_available():
        return None

    from rain.core.engine import CoreEngine

    prov = HYBRID_LLM_PROVIDER
    if not prov:
        if ANTHROPIC_API_KEY.strip():
            prov = "anthropic"
        elif OPENAI_API_KEY.strip():
            prov = "openai"
        else:
            return None
    if prov not in ("anthropic", "openai"):
        return None
    if prov == "anthropic" and not ANTHROPIC_API_KEY.strip():
        return None
    if prov == "openai" and not OPENAI_API_KEY.strip():
        return None

    model = HYBRID_LLM_MODEL
    if not model:
        model = ANTHROPIC_MODEL if prov == "anthropic" else OPENAI_MODEL
    return CoreEngine(provider=prov, model=model)


def should_route_to_hybrid_llm(prompt: str, max_tokens: int) -> bool:
    """True when this completion should use the strong (API) engine."""
    from rain.hybrid_config import should_route_to_hybrid_llm as _impl

    return _impl(prompt, max_tokens)
