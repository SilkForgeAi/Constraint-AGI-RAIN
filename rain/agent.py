"""
Rain Agent — main orchestration.
Phase 1: Core mind + tools + memory + safety
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any

import re

if TYPE_CHECKING:
    from rain.agency.autonomous import ApprovalCallback

from rain.grounding import (
    get_bounded_curiosity_instruction,
    get_constraints_instruction,
    get_corrigibility_boost,
    get_direct_answer_goal_instruction,
    get_distribution_shift_instruction,
    get_grounding_reminder,
    get_memory_citation_instruction,
    get_reasoning_boost,
    get_self_audit_grounding_check,
    get_system_prompt,
    is_hard_reasoning_query,
    needs_constraints_instruction,
    needs_corrigibility_boost,
    needs_deep_reasoning,
    needs_direct_answer_goal,
    needs_grounding_reminder,
    needs_self_audit,
    get_engineering_spec_instruction,
    needs_engineering_spec_prompt,
)
from rain.sovereign_tone import (
    get_sovereign_spec_schema_instruction,
    get_sovereign_td_instruction,
    get_tegp_kernel_instruction,
    sovereign_td_active,
)
from rain.agency.runner import (
    execute_tool_calls,
    format_tool_results,
    format_tools_for_prompt,
    parse_tool_calls,
)
from rain.agency.tools import create_default_tools
from rain.config import (
    BLAST_RADIUS_ENABLED,
    BLAST_RADIUS_THRESHOLD,
    BOUNDED_CURIOSITY_ENABLED,
    BOUNDED_CURIOSITY_MAX_SUGGESTIONS,
    CALIBRATION_ENABLED,
    CAPABILITY_GATING_ENABLED,
    CODE_EXEC_ENABLED,
    COT_ENABLED,
    COT_VERIFY_PASS,
    DEEP_REASONING_PATHS,
    AUTO_HARD_MODE,
    MATH_VERIFY_ENABLED,
    EPISTEMIC_GATE_ENABLED,
    EPISTEMIC_GATE_SAMPLES,
    EPISTEMIC_GATE_AGREE_MIN,
    INVARIANCE_CACHE_ENABLED,
    DATA_DIR,
    DEFER_CONFIDENCE_THRESHOLD,
    ENABLE_RESPONSE_CACHE,
    FETCH_URL_ALLOWLIST,
    FETCH_URL_ENABLED,
    LIST_DIR_ENABLED,
    MAX_CONTEXT_CHARS,
    MAX_HISTORY_TURNS,
    MAX_RESPONSE_TOKENS,
    ATTEMPT_MAX_RESPONSE_TOKENS,
    MEMORY_RETRIEVAL_TOP_K,
    METACOG_ENABLED,
    RAG_ALWAYS_INJECT,
    RAG_ENABLED,
    RAG_TOP_K,
    READ_FILE_ENABLED,
    SEARCH_ENABLED,
    OUTBOUND_NETWORK_ALLOWED,
    SESSION_WORLD_MODEL_ENABLED,
    SESSION_STATE_TIER2,
    WHAT_IF_ENABLED,
    BOUNDED_SEARCH_ENABLED,
    CALIBRATION_TIER3,
    ABDUCTION_TIER3,
    FORMALIZATION_TIER3,
    PROVENANCE_TIER3,
    MEMORY_REASONING_TIER3,
    TEMPORAL_TIER3,
    UNIFICATION_LAYER_ENABLED,
    COMPLETENESS_EXPANSION_ENABLED,
    GLOBAL_COHERENCE_ENABLED,
    SPEED_PRIORITY,
    SKIP_OUTPUT_GROUNDING,
    USER_NAME,
    VERIFICATION_ENABLED,
    DECISION_LAYER_ENABLED,
    AGENTIC_MAX_ROUNDS_DEFAULT,
    SESSION_TOOL_BUDGET_MAX,
    TURN_FEEDBACK_LOG_ENABLED,
    KNOWLEDGE_FACTS_TOOL_ENABLED,
    GI_STACK_ENABLED,
    GI_STRICT_ROUTING,
    STRUCTURED_MEMORY_V2_ENABLED,
    ENGINEERING_SPEC_MODE,
    RED_TEAM_PASS,
    RED_TEAM_MAX_TOKENS,
    SYMBOLIC_TREE_PLANNING,
    SYMBOLIC_THINK_ENABLED,
    SYMBOLIC_THINK_ON_CRITICAL,
    SYMBOLIC_THINK_MAX_NODES,
)
try:
    from rain.config import (
        CONTINUOUS_WORLD_MODEL_ENABLED,
        SELF_MODEL_ENABLED,
        COGNITIVE_ENERGY_ENABLED,
        MULTI_AGENT_COGNITION_ENABLED,
        MULTI_AGENT_USE_FOR_CRITICAL_ONLY,
        BIOLOGICAL_SLEEP_EVERY_N_INTERACTIONS,
        VISION_ENABLED,
        SPATIAL_REASONING_ENABLED,
    )
except Exception:
    CONTINUOUS_WORLD_MODEL_ENABLED = False
    SELF_MODEL_ENABLED = True
    COGNITIVE_ENERGY_ENABLED = False
    MULTI_AGENT_COGNITION_ENABLED = False
    MULTI_AGENT_USE_FOR_CRITICAL_ONLY = True
    BIOLOGICAL_SLEEP_EVERY_N_INTERACTIONS = 0
    VISION_ENABLED = True
    SPATIAL_REASONING_ENABLED = True
from rain.core.engine import CoreEngine
from rain.core.routing_engine import RoutingCoreEngine, build_routing_engine
from rain.governance.audit import AuditLog
from rain.governance.shared_context import get_shared_context
from rain.memory.store import MemoryStore
from rain.meta.metacog import MetaCognition
from rain.planning.planner import Planner
from rain.reasoning.causal import CausalInference
from rain.reasoning.deep import multi_path_reasoning
from rain.reasoning.verify import is_critical_prompt, should_verify, verify_response
from rain.world.simulator import WorldSimulator
from rain.agency.goal_stack import GoalStack
from rain.capabilities.observation import ObservationBuffer
from rain.safety.grounding_filter import response_without_hidden_reasoning, strip_emojis, violates_grounding
from rain.safety.retrieval_sanitizer import sanitize_chunk
from rain.safety.vault import SAFETY_OVERRIDE_REFUSAL, SafetyVault
from rain.classification import (
    _is_creative_prompt,
    _is_counterfactual_prompt,
    _is_attempt_requested_prompt,
    _is_epistemic_halt_or_defer_response,
    _is_structured_cross_domain_invention_prompt,
    _is_continuation_prompt,
    _is_acknowledgment_prompt,
    _is_factual_query,
    _is_agi_discriminator_eval_prompt,
)


def _skip_output_grounding() -> bool:
    """True if output grounding filter should be skipped (config at import + runtime env).

    run.py may set RAIN_SKIP_OUTPUT_GROUNDING after ``rain.config`` was imported; re-read env here.
    """
    if SKIP_OUTPUT_GROUNDING:
        return True
    return os.getenv("RAIN_SKIP_OUTPUT_GROUNDING", "").strip().lower() in ("true", "1", "yes")


class Rain:
    """Rain — AGI cognitive stack agent."""

    def _cognitive_pre_llm_system(
        self,
        system: str,
        prompt: str,
        *,
        use_tools: bool,
        use_memory: bool,
    ) -> str:
        """Session/task world + GI stack + Router v2 (see rain/integration/cognitive_inject.py)."""
        try:
            from rain.integration.cognitive_inject import apply_pre_llm_system

            return apply_pre_llm_system(
                self,
                system,
                prompt,
                use_tools=use_tools,
                use_memory=use_memory,
                safety_allowed=True,
            )
        except Exception:
            return system

    def __init__(self):
        # Memory
        self.memory = MemoryStore(DATA_DIR)
        # Bootstrap user identity from env (e.g. RAIN_USER_NAME=Aaron)
        if USER_NAME:
            try:
                from rain.memory.user_identity import recall_user_identity, store_user_identity
                existing = recall_user_identity(self.memory)
                if not existing.get("name"):
                    store_user_identity(self.memory, USER_NAME)
            except Exception:
                pass

        # Core (optional hybrid: local Ollama + API for heavy/sovereign — see rain/hybrid_config.py)
        self.engine = build_routing_engine()
        self.planner = Planner(self.engine)
        self.metacog = MetaCognition(self.engine)
        self.simulator = WorldSimulator(self.engine)
        self.causal = CausalInference(self.engine)

        # Agency
        self.tools = create_default_tools()
        self._register_memory_tool()

        # Safety & governance
        self.safety = SafetyVault()
        self.audit = AuditLog(DATA_DIR / "audit.log")
        self.shared_context = get_shared_context()
        from rain.orchestration.explore_exploit import SessionExploreBudget

        self._explore_budget = SessionExploreBudget()
        self._turn_decision = None
        # Capability gating: when enabled, restricted tools need this callback to approve
        self.tool_approval_callback: Any = None
        self._current_memory_namespace: str | None = None
        # Robust agency (in-session only): goal stack + observation buffer for grounding
        self.goal_stack = GoalStack()
        self.observation_buffer = ObservationBuffer()
        # Scale/efficiency: optional response cache (buyer can enable via RAIN_ENABLE_RESPONSE_CACHE=1)
        self._response_cache = None
        if ENABLE_RESPONSE_CACHE:
            from rain.capabilities.efficiency import ResponseCache
            self._response_cache = ResponseCache()
        # Full subsystems: self-model, cognitive energy, continuous world model
        self._self_model = None
        self._cognitive_energy = None
        self._continuous_world_model = None
        self._think_count = 0
        self._session_world_model = None
        self._session_world_state = None
        try:
            from rain.config import SESSION_STATE_TIER2
            from rain.world.session_state import SessionWorldState
            if SESSION_STATE_TIER2:
                self._session_world_state = SessionWorldState()
        except Exception:
            pass
        self._register_voice_tool()
        if VISION_ENABLED:
            self._register_vision_tool()
        if SPATIAL_REASONING_ENABLED:
            self._register_spatial_tool()

    def _register_voice_tool(self) -> None:
        """Register voice_transcribe tool when voice stack is available."""
        try:
            from rain.config import VOICE_PROFILES_DB
            from rain.voice.backends.mock import MockVoiceBackend
            from rain.voice.service import VoiceService
            from rain.memory.voice_profiles import VoiceProfileStore
            backend = MockVoiceBackend()
            if not getattr(__import__("rain.config", fromlist=["SKIP_VOICE_LOAD"]), "SKIP_VOICE_LOAD", False):
                try:
                    from rain.voice.backends.whisper_local import get_whisper_backend
                    if get_whisper_backend():
                        backend = get_whisper_backend()
                except Exception:
                    pass
            store = VoiceProfileStore(VOICE_PROFILES_DB)
            voice_svc = VoiceService(backend, store)

            def voice_transcribe(audio_path: str) -> str:
                """Transcribe audio and identify speaker. Returns 'Transcript: ... Speaker: ...' for use in context."""
                from pathlib import Path
                p = Path(audio_path)
                if not p.exists():
                    return f"Error: file not found: {audio_path}"
                result = voice_svc.transcribe_and_identify(p)
                text = result.full_text.strip() or "(no speech detected)"
                primary = result.segments[0].speaker_id if result.segments else "Speaker 0"
                return f"Transcript: {text}\nSpeaker: {primary}"

            self.tools.register(
                "voice_transcribe",
                voice_transcribe,
                "Transcribe audio file and identify speaker. Params: audio_path (path to .wav or audio file). Returns transcript and speaker id/name.",
                {"audio_path": "str"},
            )
        except Exception:
            pass  # Voice optional; skip if deps missing

    def _register_vision_tool(self) -> None:
        """Register describe_image for embodied perception (vision)."""
        try:
            from rain.tools.vision import describe_image
            def _describe(image_path: str = "", image_base64: str = "") -> str:
                return describe_image(image_path=image_path, image_base64=image_base64, engine=self.engine)
            self.tools.register(
                "describe_image",
                _describe,
                "Describe the content of an image. Params: image_path (file path) or image_base64 (base64 string).",
                {"image_path": "str", "image_base64": "str"},
            )
        except Exception:
            pass

    def _register_spatial_tool(self) -> None:
        """Register spatial_reason for embodied perception (spatial reasoning)."""
        try:
            from rain.tools.spatial import spatial_reason
            def _spatial(description: str, query: str) -> str:
                return spatial_reason(description, query, engine=self.engine)
            self.tools.register(
                "spatial_reason",
                _spatial,
                "Answer a spatial query given a text description of layout/environment. Params: description (str), query (str).",
                {"description": "str", "query": "str"},
            )
        except Exception:
            pass

    def _get_self_model(self):
        if self._self_model is None and SELF_MODEL_ENABLED:
            from rain.meta.self_model import SelfModel
            self._self_model = SelfModel(DATA_DIR)
        return self._self_model

    def _get_cognitive_energy(self):
        if self._cognitive_energy is None and COGNITIVE_ENERGY_ENABLED:
            from rain.capabilities.cognitive_energy import get_cognitive_energy_model
            self._cognitive_energy = get_cognitive_energy_model()
        return self._cognitive_energy

    def _get_session_world_model(self):
        """Lazy init session world model (recent turn summaries)."""
        if self._session_world_model is None and SESSION_WORLD_MODEL_ENABLED:
            from rain.world.session_model import SessionWorldModel
            self._session_world_model = SessionWorldModel(max_entries=20, max_chars_per_entry=200)
        return self._session_world_model

    def _get_continuous_world_model(self):
        if self._continuous_world_model is None and CONTINUOUS_WORLD_MODEL_ENABLED:
            from rain.world.continuous_simulator import get_continuous_world_model
            self._continuous_world_model = get_continuous_world_model(simulator=self.simulator, engine=self.engine)
        return self._continuous_world_model

    def _register_memory_tool(self) -> None:
        """Allow Rain to store experiences via tools."""

        def remember(content: str) -> str:
            ns = getattr(self, "_current_memory_namespace", None)
            vid = self.memory.remember_experience(content, namespace=ns)
            return "Remembered." if vid else "Not stored (filtered by policy)."

        def remember_skill(procedure: str) -> str:
            ns = getattr(self, "_current_memory_namespace", None)
            vid = self.memory.remember_skill(procedure, namespace=ns)
            return "Skill stored." if vid else "Not stored (filtered by policy)."

        self.tools.register(
            "remember",
            remember,
            "Store an experience or fact in long-term memory. Params: content (str)",
            {"content": "str"},
        )
        self.tools.register(
            "remember_skill",
            remember_skill,
            "Store procedural knowledge (how to do X). Params: procedure (str)",
            {"procedure": "str"},
        )

        if KNOWLEDGE_FACTS_TOOL_ENABLED:
            def remember_fact(subject: str, predicate: str, obj: str = "") -> str:
                from rain.knowledge.facts import get_fact_store

                ns = getattr(self, "_current_memory_namespace", None)
                if not ns:
                    return "Not stored (no active memory namespace)."
                get_fact_store(DATA_DIR).add_fact(subject, predicate, obj, namespace=ns, source="tool")
                return "Structured fact recorded."

            self.tools.register(
                "remember_fact",
                remember_fact,
                "Store a subject–predicate–object fact for structured retrieval in later turns. Params: subject, predicate, object (optional)",
                {"subject": "str", "predicate": "str", "object": "str"},
            )

        def simulate(state: str, action: str) -> str:
            return self.simulator.simulate(state, action)

        def simulate_rollout(state: str, actions: str) -> str:
            """Multi-step hypothetical: state + action1; action2; ... -> chained outcomes. Max 5 steps. No real action."""
            return self.simulator.simulate_rollout(state, actions)

        def infer_causes(effect: str, candidates: str = "") -> str:
            result = self.causal.infer_causes(effect, candidates)
            # Store in causal memory for lifelong learning
            try:
                from rain.memory.causal_memory import store_causal
                cause_summary = result[:150].replace("\n", " ").strip()
                if cause_summary:
                    ns = getattr(self, "_current_memory_namespace", None)
                    store_causal(self.memory, cause=cause_summary, effect=effect[:100], mechanism="inferred", namespace=ns)
            except Exception:
                pass
            return result

        def query_causes(effect: str) -> str:
            """Query stored cause-effect links for an effect. Use after infer_causes has been used (stores results)."""
            try:
                from rain.memory.causal_memory import recall_causal
                ns = getattr(self, "_current_memory_namespace", None)
                links = recall_causal(self.memory, effect, limit=5, namespace=ns)
                if not links:
                    return "No stored causes for that effect. Use infer_causes to analyze and store."
                parts = []
                for i, link in enumerate(links, 1):
                    cause = link.get("cause", "")
                    eff = link.get("effect", "")
                    conf = link.get("confidence", "")
                    mech = link.get("mechanism", "")
                    parts.append(f"[{i}] Cause: {cause}\n  Effect: {eff}\n  Confidence: {conf}" + (f"\n  Mechanism: {mech}" if mech else ""))
                return "\n\n".join(parts)
            except Exception as e:
                return f"Error querying causal store: {str(e)[:150]}"

        def store_lesson(situation: str, approach: str, outcome: str) -> str:
            from rain.learning.lessons import store_lesson as _store_lesson
            ns = getattr(self, "_current_memory_namespace", None)
            ok = _store_lesson(self.memory, situation, approach, outcome, namespace=ns)
            return "Lesson stored." if ok else "Not stored (filtered)."

        self.tools.register("simulate", simulate, "Hypothetical: what might happen if action in state? Params: state, action", {"state": "str", "action": "str"})
        self.tools.register("simulate_rollout", simulate_rollout, "Multi-step hypothetical: state then semicolon-separated actions (e.g. 'do A; then B; then C'). Returns chained outcomes. Max 5 steps. Params: state, actions", {"state": "str", "actions": "str"})
        self.tools.register("infer_causes", infer_causes, "Causal analysis: likely causes of effect. Params: effect, candidates (optional)", {"effect": "str", "candidates": "str"})
        self.tools.register("query_causes", query_causes, "Query stored cause-effect links for an effect (from prior infer_causes). Params: effect", {"effect": "str"})
        self.tools.register("store_lesson", store_lesson, "Store lesson from feedback: when situation, approach led to outcome. Params: situation, approach, outcome", {"situation": "str", "approach": "str", "outcome": "str"})

        def record_belief(claim: str, confidence: float, source: str = "") -> str:
            from rain.memory.belief_memory import store_belief
            conf = max(0.0, min(1.0, float(confidence)))
            if CALIBRATION_ENABLED and not SPEED_PRIORITY and conf >= 0.8:
                try:
                    from rain.meta.calibration import check_belief_consistency
                    consistent, suggested = check_belief_consistency(self.engine, claim, conf)
                    if not consistent:
                        conf = suggested
                except Exception:
                    pass
            ns = getattr(self, "_current_memory_namespace", None)
            ok = store_belief(self.memory, claim, conf, source, namespace=ns)
            return "Belief recorded." if ok else "Not stored."
        self.tools.register("record_belief", record_belief, "Record a belief with confidence (0-1). Params: claim (str), confidence (float), source (optional str)", {"claim": "str", "confidence": "float", "source": "str"})

        def consolidate_memories() -> str:
            """Run memory consolidation: prune old low-importance memories. Call periodically."""
            from rain.learning.lifelong import consolidate
            pruned = consolidate(self.memory, max_total=500, prune_below_importance=0.25, prune_older_days=90)
            return f"Consolidation complete. Pruned {pruned} memories."
        self.tools.register("consolidate_memories", consolidate_memories, "Maintain memory: prune old low-importance memories. No params.", {})

        def should_use_qpu(goal: str, context: str = "") -> str:
            """Check whether this goal should be routed to QPU (quantum) vs classical. Returns route type, reason, and if quantum: suggested problem type and complexity. Use when user asks about optimization, routing, or quantum."""
            try:
                from rain.routing.compute_router import compute_route
                from rain import config as rain_config
                route = compute_route(goal, steps=None, context=context, enabled=rain_config.QPU_ROUTER_ENABLED)
                out = f"Route: {route.route_type}. Reason: {route.reason}. Confidence: {route.confidence}."
                if route.route_type == "quantum":
                    out += f" Suggested problem type: {route.suggested_problem_type or 'routing'}. Complexity: {route.complexity_estimate}."
                return out
            except Exception as e:
                return f"Error checking compute route: {e}"
        self.tools.register(
            "should_use_qpu",
            should_use_qpu,
            "Check if a goal should use QPU (quantum) vs classical compute. Params: goal (str), context (optional str). Use for optimization/routing questions.",
            {"goal": "str", "context": "str"},
        )

        if SEARCH_ENABLED and OUTBOUND_NETWORK_ALLOWED:
            try:
                from rain.tools.search import web_search
                self.tools.register("search", web_search, "Search the web. Params: query (str), max_results (int, default 5)", {"query": "str", "max_results": "int"})
            except Exception:
                pass

        if CODE_EXEC_ENABLED:
            try:
                from rain.tools.code_exec import execute_code
                self.tools.register(
                    "run_code",
                    lambda code: execute_code(code),
                    "Execute Python code in sandbox (math, json, re, datetime only). Set 'result' variable. Params: code (str)",
                    {"code": "str"},
                )
            except Exception:
                pass

        if READ_FILE_ENABLED:
            try:
                from rain.tools.read_file import read_file as _read_file
                self.tools.register(
                    "read_file",
                    lambda relative_path: _read_file(relative_path),
                    "Read a file (project or data dir only, read-only, max 100KB). Params: relative_path (str, e.g. 'docs/README.md')",
                    {"relative_path": "str"},
                )
            except Exception:
                pass

        if LIST_DIR_ENABLED:
            try:
                from rain.tools.list_dir import list_dir as _list_dir
                self.tools.register(
                    "list_dir",
                    lambda relative_path="": _list_dir(relative_path),
                    "List directory contents (project or data dir only). Params: relative_path (str, optional, e.g. 'docs' or '')",
                    {"relative_path": "str"},
                )
            except Exception:
                pass

        if FETCH_URL_ENABLED and FETCH_URL_ALLOWLIST:
            try:
                from rain.tools.fetch_url import fetch_url as _fetch_url
                self.tools.register(
                    "fetch_url",
                    lambda url: _fetch_url(url),
                    "Fetch URL content (read-only). Only allowlisted URLs. Params: url (str)",
                    {"url": "str"},
                )
            except Exception:
                pass

        if RAG_ENABLED:
            try:
                from rain.tools.rag import add_document_chunked, query_rag

                def _format_rag(results: list) -> str:
                    if not results:
                        return "No relevant documents found."
                    parts = []
                    for i, r in enumerate(results, 1):
                        src = r.get("source", "")
                        content = (r.get("content", "") or "")[:800]
                        parts.append(f"[{i}] " + (f"({src}): " if src else "") + content)
                    return "\n\n".join(parts)

                def _add_document(content: str, source: str = "") -> str:
                    ids = add_document_chunked(content, source=source)
                    if not ids:
                        return "No content indexed."
                    return f"Indexed {len(ids)} chunk(s)."

                self.tools.register(
                    "add_document",
                    _add_document,
                    "Add a document to the RAG corpus for retrieval (chunked indexing). Params: content (str), source (str, optional)",
                    {"content": "str", "source": "str"},
                )
                self.tools.register(
                    "query_rag",
                    lambda query, top_k=5: _format_rag(query_rag(query, top_k=top_k, adaptive=True)),
                    "Search the RAG document corpus (adaptive query expansion + merge). Returns relevant passages. Params: query (str), top_k (int, default 5)",
                    {"query": "str", "top_k": "int"},
                )
                self.tools.register(
                    "search_knowledge_base",
                    lambda query, top_k=None: _format_rag(query_rag(query, top_k=top_k or RAG_TOP_K, adaptive=True)),
                    "Search the knowledge base (adaptive RAG) for relevant passages. Params: query (str), top_k (int, optional)",
                    {"query": "str", "top_k": "int"},
                )
            except Exception:
                pass

        def run_tool_chain(chain_json: str) -> str:
            from rain.agency.tool_chain import run_tool_chain as _run
            return _run(chain_json, self.tools, self.safety.check)
        self.tools.register(
            "run_tool_chain",
            run_tool_chain,
            "Execute multiple tools in sequence. Params: chain_json (JSON array, e.g. [{\"tool\":\"calc\",\"expression\":\"2+2\"},{\"tool\":\"remember\",\"content\":\"Result: {{0}}\"}]). Use {{0}},{{1}} for previous results.",
            {"chain_json": "str"},
        )


    # ── Pipeline stage methods ──────────────────────────────────────

    def _build_memory_context(
        self, prompt: str, use_memory: bool, namespace: str | None,
    ) -> str:
        """Build full memory context: retrieval, RAG, self-model, world model, cognitive energy, OOD."""
        td = getattr(self, "_turn_decision", None)
        if not use_memory:
            if td is not None:
                parts: list[str] = []
                if getattr(td, "knowledge_fragment", ""):
                    parts.append(td.knowledge_fragment)
                if getattr(td, "tom_fragment", ""):
                    parts.append(td.tom_fragment)
                if parts:
                    return "\n\n".join(parts)
            return ""
        top_k = MEMORY_RETRIEVAL_TOP_K
        if td is not None:
            top_k = td.memory_top_k
        memory_ctx = self.memory.get_context_for_query(
            prompt, max_experiences=top_k, namespace=namespace,
        )
        if td is not None:
            if getattr(td, "knowledge_fragment", ""):
                kf = td.knowledge_fragment
                memory_ctx = (memory_ctx + "\n\n" + kf) if memory_ctx else kf
            if getattr(td, "tom_fragment", ""):
                tf = td.tom_fragment
                memory_ctx = (memory_ctx + "\n\n" + tf) if memory_ctx else tf
        if RAG_ENABLED and (_is_factual_query(prompt) or RAG_ALWAYS_INJECT):
            try:
                from rain.tools.rag import query_rag
                rag_results = query_rag(prompt, top_k=RAG_TOP_K)
                if rag_results:
                    rag_parts = []
                    for r in rag_results[:5]:
                        c = sanitize_chunk((r.get("content", "") or ""), max_len=600)
                        if c:
                            rag_parts.append(c)
                    rag_blob = "\n\n".join(rag_parts) if rag_parts else ""
                    if rag_blob:
                        memory_ctx = (
                            (memory_ctx + "\n\nRetrieved documents (use when relevant):\n" + rag_blob)
                            if memory_ctx
                            else "Retrieved documents (use when relevant):\n" + rag_blob
                        )
            except Exception:
                pass
        if self.memory.is_potentially_ood(prompt, namespace):
            ood = get_distribution_shift_instruction().replace("[", "").replace("]", "").strip()
            memory_ctx = (memory_ctx + "\n\n" + ood) if memory_ctx else ood
        if SELF_MODEL_ENABLED:
            sm = self._get_self_model()
            if sm:
                sm_ctx = sm.get_self_model_context(max_length=1000)
                memory_ctx = (memory_ctx + "\n\n" + sm_ctx) if memory_ctx else sm_ctx
        if CONTINUOUS_WORLD_MODEL_ENABLED:
            cwm = self._get_continuous_world_model()
            if cwm:
                cwm_ctx = cwm.get_context_for_prompt(max_length=600)
                memory_ctx = (memory_ctx + "\n\n" + cwm_ctx) if memory_ctx else cwm_ctx
        if COGNITIVE_ENERGY_ENABLED:
            ce = self._get_cognitive_energy()
            if ce:
                ce.set_focus(prompt[:150])
                ce_ctx = ce.get_status_for_prompt(200)
                memory_ctx = (memory_ctx + "\n\n" + ce_ctx) if memory_ctx else ce_ctx
        if len(memory_ctx) > MAX_CONTEXT_CHARS:
            memory_ctx = memory_ctx[:MAX_CONTEXT_CHARS] + "\n\n[Context truncated for efficiency.]"
        return memory_ctx

    def _build_system_context(
        self,
        prompt: str,
        memory_ctx: str,
        history: list[dict[str, str]],
    ) -> tuple[str, str, list[dict[str, str]], list]:
        """Assemble system prompt, user content, messages array, and parsed constraints."""
        from rain.advance.stack import extra_system_instructions
        system = get_system_prompt()
        if needs_grounding_reminder(prompt):
            system += get_grounding_reminder()
        if needs_corrigibility_boost(prompt):
            system += get_corrigibility_boost()
        if needs_direct_answer_goal(prompt):
            system += get_direct_answer_goal_instruction()
        if needs_constraints_instruction(prompt):
            system += get_constraints_instruction()
        if needs_self_audit(prompt) and history:
            audit_note = get_self_audit_grounding_check(history)
            if audit_note:
                system += audit_note
        if BOUNDED_CURIOSITY_ENABLED:
            system += get_bounded_curiosity_instruction(BOUNDED_CURIOSITY_MAX_SUGGESTIONS)
        system += get_reasoning_boost(prompt)
        if ENGINEERING_SPEC_MODE or needs_engineering_spec_prompt(prompt):
            system += "\n\n" + get_engineering_spec_instruction()
        try:
            if sovereign_td_active(prompt):
                system += "\n\n" + get_sovereign_td_instruction()
                system += "\n\n" + get_tegp_kernel_instruction()
        except Exception:
            pass
        system += extra_system_instructions(prompt)
        if TEMPORAL_TIER3 and needs_deep_reasoning(prompt):
            try:
                from rain.reasoning.temporal import temporal_reasoning_instruction
                system += "\n\n" + temporal_reasoning_instruction()
            except Exception:
                pass
        try:
            from rain.reasoning.premise_check import detect_premise, check_premise, PREMISE_DISCLAIMER
            premise = detect_premise(prompt)
            if premise:
                ok, _reason = check_premise(self.engine, premise)
                if not ok:
                    system += "\n\n" + PREMISE_DISCLAIMER + " State this at the start of your response."
        except Exception:
            pass
        if COT_ENABLED and needs_deep_reasoning(prompt):
            try:
                from rain.reasoning.belief_slice import get_uncertainty_context
                uc = get_uncertainty_context(self.memory)
                if uc:
                    system += "\n\n" + uc
            except Exception:
                pass
        if COT_ENABLED and needs_deep_reasoning(prompt):
            from rain.world.coherent_model import world_model_context_for_prompt
            system += "\n\n" + world_model_context_for_prompt()
        if _is_attempt_requested_prompt(prompt):
            system += (
                "\n\n[Attempt requested] The user asked for an attempted solution, proof strategy, or step-by-step work. "
                "Do not refuse with uncertainty or ask to narrow the question; provide your reasoning and partial results, "
                "and clearly label any speculative steps."
            )
        content = prompt
        if memory_ctx:
            content = f"Memory:\n{memory_ctx}\n\nUser: {prompt}"
            system += get_memory_citation_instruction()
        system = self._cognitive_pre_llm_system(
            system, prompt, use_tools=False, use_memory=bool(memory_ctx),
        )
        if DECISION_LAYER_ENABLED and getattr(self, "_turn_decision", None) is not None:
            try:
                from rain.orchestration.decision_layer import decision_system_addon

                system += decision_system_addon(self._turn_decision)
            except Exception:
                pass
        constraints: list = []
        try:
            from rain.reasoning.constraint_tracker import parse_constraints_from_prompt, checklist_instruction
            constraints = parse_constraints_from_prompt(prompt)
            if constraints:
                content = content + "\n\n" + checklist_instruction(constraints)
        except Exception:
            pass
        if getattr(self, "_session_world_state", None):
            summary = self._session_world_state.get_summary_for_prompt()
            if summary:
                content = content + "\n\n" + summary
        messages = [
            {"role": "system", "content": system},
            *history,
            {"role": "user", "content": content},
        ]
        return system, content, messages, constraints

    def _run_symbolic_node_reasoning(
        self,
        prompt: str,
        memory_ctx: str,
        messages: list[dict[str, str]],
        *,
        max_tokens: int,
        force: bool = False,
    ) -> str:
        """Run deterministic plan-tree node filling with per-node verification.

        Returns final refined text when symbolic path succeeds, else empty string so
        caller can fall back to standard reasoning.
        """
        if not SYMBOLIC_TREE_PLANNING and not force:
            return ""
        if not SYMBOLIC_THINK_ENABLED and not force:
            return ""
        # FakeEngine in tests and some thin wrappers don't implement reason().
        if not hasattr(self, "engine") or not hasattr(self.engine, "reason"):
            return ""
        try:
            from rain.planning.planner import plan_with_symbolic_tree
            from rain.reasoning.symbolic_verifier import verify_node_output

            goal_for_tree = (prompt or "").strip()[:800]
            tree, _steps = plan_with_symbolic_tree(
                goal_for_tree,
                context=(memory_ctx or "")[:400] if memory_ctx else "",
                engine=self.engine,
            )
            node_results: list[str] = []
            guard = 0
            while not tree.is_complete() and guard < SYMBOLIC_THINK_MAX_NODES:
                node = tree.get_next_node()
                if not node:
                    break
                tree.mark_in_progress(node.id)
                node_prompt = (
                    f"Single node task (dependencies verified).\n"
                    f"Goal: {goal_for_tree}\n"
                    f"Node: {node.description}\n"
                    "Output ONLY what this node requires. No plan. No preamble."
                )
                node_messages = [
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": node_prompt},
                ]
                node_out = self.engine.complete(
                    node_messages, temperature=0.35, max_tokens=1024
                ).strip()
                ok, msg = verify_node_output(node, node_out)
                if not ok:
                    retry_prompt = (
                        node_prompt
                        + "\n\nVerification failed: "
                        + msg
                        + "\nFix the output so it is non-empty and any code/numeric claims are valid."
                    )
                    retry_messages = [
                        {"role": "system", "content": get_system_prompt()},
                        {"role": "user", "content": retry_prompt},
                    ]
                    retry_out = self.engine.complete(
                        retry_messages, temperature=0.25, max_tokens=1024
                    ).strip()
                    ok2, msg2 = verify_node_output(node, retry_out)
                    node_out = retry_out if ok2 else node_out
                    ok = ok2
                    msg = msg2 if ok2 else msg
                tree.submit_result(node.id, node_out, ok, msg or "")
                node_results.append(node_out)
                guard += 1

            joined = ("\n\n".join(node_results) or "").strip()
            if not joined:
                return ""
            refine_msgs = messages + [
                {"role": "assistant", "content": joined},
                {
                    "role": "user",
                    "content": "Refine this into a single coherent final response. "
                    "Keep within constraints; output only the improved final response.",
                },
            ]
            return self.engine.complete(refine_msgs, temperature=0.3, max_tokens=max_tokens)
        except Exception:
            return ""

    def _run_reasoning(
        self,
        prompt: str,
        messages: list[dict[str, str]],
        content: str,
        system: str,
        history: list[dict[str, str]],
        constraints: list,
        memory_ctx: str,
    ) -> str:
        """Execute core reasoning: what-if, abduction, general chain, multi-path, draft-refine, or fallback."""
        if WHAT_IF_ENABLED and not SPEED_PRIORITY:
            try:
                from rain.reasoning.what_if import detect_what_if, query_what_if
                intervention = detect_what_if(prompt)
                if intervention:
                    ans, _ = query_what_if(self.engine, prompt, intervention, context=memory_ctx or "")
                    if ans:
                        if getattr(self, "_session_world_state", None):
                            self._session_world_state.update_from_turn(prompt, ans)
                        return ans
            except Exception:
                pass

        if ABDUCTION_TIER3 and not SPEED_PRIORITY and needs_deep_reasoning(prompt) and ("why" in prompt.lower() or "explain" in prompt.lower()):
            try:
                from rain.reasoning.abduction import abduce
                best, _ = abduce(self.engine, prompt[:400], context=memory_ctx or "", n_hypotheses=2)
                if best:
                    content = content + "\n\n[Best hypothesis to consider]: " + best[:250]
                    messages = [{"role": "system", "content": system}, *history, {"role": "user", "content": content}]
            except Exception:
                pass

        if COT_ENABLED and needs_deep_reasoning(prompt) and memory_ctx:
            try:
                from rain.reasoning.general import reason_explain
                chain = reason_explain(self.engine, prompt[:300], context=memory_ctx[:400])
                if chain and len(chain) > 20:
                    content = content + "\n\n[Reasoning chain]: " + chain[:500]
                    messages = [
                        {"role": "system", "content": system},
                        *history,
                        {"role": "user", "content": content},
                    ]
            except Exception:
                pass

        if COT_ENABLED and needs_deep_reasoning(prompt):
            effective_paths = DEEP_REASONING_PATHS if DEEP_REASONING_PATHS >= 2 else (2 if (AUTO_HARD_MODE and is_hard_reasoning_query(prompt)) else 0)
            if is_critical_prompt(prompt):
                effective_paths = max(effective_paths, 2)
            if _is_attempt_requested_prompt(prompt):
                effective_paths = 1
            budget = max(1024, MAX_RESPONSE_TOKENS)
            attempt_cap = ATTEMPT_MAX_RESPONSE_TOKENS if _is_attempt_requested_prompt(prompt) else 8192
            if _is_attempt_requested_prompt(prompt):
                budget = max(budget, attempt_cap)
            max_tokens_path = max(1024, min(attempt_cap, budget // max(1, effective_paths)))
            if effective_paths >= 2:
                symbolic = self._run_symbolic_node_reasoning(
                    prompt, memory_ctx, messages, max_tokens=max_tokens_path, force=False
                )
                if symbolic:
                    return symbolic
                if BOUNDED_SEARCH_ENABLED and is_critical_prompt(prompt):
                    from rain.reasoning.bounded_search import budgeted_search
                    return budgeted_search(
                        self.engine, messages, prompt=prompt, memory=self.memory,
                        goal=self.goal_stack.current_goal(),
                        beam_width=min(effective_paths, 3), max_depth=2,
                        max_tokens_per_path=max_tokens_path,
                    )
                return multi_path_reasoning(self.engine, messages, num_paths=effective_paths, max_tokens_per_path=max_tokens_path, prompt=prompt, constraints=constraints, goal=self.goal_stack.current_goal())
            else:
                draft = self.engine.complete(messages, temperature=0.5, max_tokens=max_tokens_path)
                refine_msgs = messages + [
                    {"role": "assistant", "content": draft},
                    {"role": "user", "content": "Refine this response: fix any errors, clarify unclear parts, improve structure. Output only the improved response, no meta-commentary."},
                ]
                return self.engine.complete(refine_msgs, temperature=0.3, max_tokens=max_tokens_path)
        elif (
            SYMBOLIC_THINK_ENABLED
            and SYMBOLIC_THINK_ON_CRITICAL
            and is_critical_prompt(prompt)
            and not _is_attempt_requested_prompt(prompt)
            and not SPEED_PRIORITY
        ):
            symbolic = self._run_symbolic_node_reasoning(
                prompt, memory_ctx, messages, max_tokens=1024, force=True
            )
            if symbolic:
                return symbolic
        elif SPEED_PRIORITY:
            _stream_tok = max(1024, ATTEMPT_MAX_RESPONSE_TOKENS) if _is_attempt_requested_prompt(prompt) else 1024
            return "".join(self.engine.complete_stream(messages, temperature=0.6, max_tokens=_stream_tok)).strip()
        else:
            _fallback_tok = max(1024, ATTEMPT_MAX_RESPONSE_TOKENS) if _is_attempt_requested_prompt(prompt) else 1024
            return self.engine.complete(messages, temperature=0.6, max_tokens=_fallback_tok)

    def _verify_and_gate(
        self,
        prompt: str,
        messages: list[dict[str, str]],
        response: str,
        memory_ctx: str,
    ) -> tuple[str, bool, bool | None]:
        """Verification loop, epistemic gate, math verify, proof check, constraint check.

        Returns (response, verify_ran, verify_ok).
        """
        _verify_ran = False
        _verify_ok: bool | None = None

        if VERIFICATION_ENABLED and not SPEED_PRIORITY and (
            should_verify(prompt, response)
            or is_critical_prompt(prompt)
            or (COT_VERIFY_PASS and needs_deep_reasoning(prompt))
        ):
            _verify_ran = True
            ok, note = verify_response(self.engine, prompt, response)
            _verify_ok = ok
            try:
                from rain.advance.stack import log_verification_result
                log_verification_result(ok, prompt[:200], note if not ok else None)
            except Exception:
                pass
            if not ok and note:
                try:
                    from rain.reasoning.belief_slice import update as belief_update
                    claim = (response or "")[:120].strip().split(".")[0] + "." if response else ""
                    if len(claim) > 10:
                        belief_update(self.memory, claim, 0.3, supported=False, namespace=getattr(self, "_current_memory_namespace", None))
                except Exception:
                    pass
                retry_msgs = messages + [
                    {"role": "assistant", "content": response},
                    {"role": "user", "content": f"Your previous response had issues: {note}. Please correct and try again. Output only the improved response."},
                ]
                response = self.engine.complete(retry_msgs, temperature=0.3, max_tokens=1024)

                _note_l = (note or "").lower()
                _needs_logical_audit = any(k in _note_l for k in (
                    "logic", "contradict", "unsupported", "assumption", "derivation", "math", "inconsisten"
                ))
                if _needs_logical_audit:
                    audit_msgs = messages + [
                        {"role": "assistant", "content": response},
                        {
                            "role": "user",
                            "content": (
                                "Perform a strict logical audit of your previous response. "
                                "Identify and fix unsupported assumptions, invalid derivations, internal contradictions, "
                                "and math inconsistencies. Keep valid parts unchanged. Output only the corrected response."
                            ),
                        },
                    ]
                    response = self.engine.complete(audit_msgs, temperature=0.2, max_tokens=1024)

                if is_critical_prompt(prompt):
                    ok2, note2 = verify_response(self.engine, prompt, response)
                    if not ok2 and note2:
                        response = response + "\n\n[Note: This is high-stakes; please verify important details independently.]"

        if (
            EPISTEMIC_GATE_ENABLED
            and not SPEED_PRIORITY
            and (is_critical_prompt(prompt) or needs_deep_reasoning(prompt))
            and not _is_attempt_requested_prompt(prompt)
        ):
            try:
                from rain.reasoning.epistemic_gate import should_halt, HALT_MESSAGE
                halt, _ = should_halt(
                    self.engine, messages,
                    num_samples=EPISTEMIC_GATE_SAMPLES,
                    agree_min=EPISTEMIC_GATE_AGREE_MIN,
                    existing_response=response,
                )
                if halt:
                    response = HALT_MESSAGE
            except Exception:
                pass

        if MATH_VERIFY_ENABLED and not SPEED_PRIORITY:
            try:
                from rain.reasoning.math_verify import is_math_like_prompt, verify_math_steps
                if is_math_like_prompt(prompt):
                    ok, note = verify_math_steps(prompt, response)
                    if not ok and note:
                        retry_msgs = messages + [
                            {"role": "assistant", "content": response},
                            {"role": "user", "content": f"Math check: {note} Please correct and output the improved response."},
                        ]
                        response = self.engine.complete(retry_msgs, temperature=0.3, max_tokens=1024)
            except Exception:
                pass

        try:
            from rain.reasoning.math_verify import is_math_like_prompt
            from rain.reasoning.exact_math import substitute_exact_math
            if is_math_like_prompt(prompt):
                def _calc(expr):
                    return self.tools.execute("calc", expression=expr)
                _before_math = response
                response = substitute_exact_math(prompt, response, _calc)
                if response != _before_math:
                    try:
                        self.audit.log(
                            "exact_math_substitution",
                            {"prompt_preview": prompt[:120], "before_len": len(_before_math or ""), "after_len": len(response or "")},
                            outcome="ok",
                        )
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            from rain.grounding import needs_proof_hooks
            from rain.reasoning.proof_fragment import extract_proof_steps_from_response, verify_propositional_steps
            if needs_proof_hooks(prompt) and (response or ""):
                steps = extract_proof_steps_from_response(response)
                if steps:
                    ok, msg = verify_propositional_steps(steps)
                    if ok and FORMALIZATION_TIER3:
                        try:
                            from rain.reasoning.formalization import compose_proof_steps
                            _, summary = compose_proof_steps(steps)
                            if summary:
                                response = response + "\n\n[Formal summary]: " + summary
                        except Exception:
                            pass
                    if not ok and msg:
                        retry_msgs = messages + [
                            {"role": "assistant", "content": response},
                            {"role": "user", "content": f"Proof check failed: {msg}. Correct the proof steps and output the improved response."},
                        ]
                        response = self.engine.complete(retry_msgs, temperature=0.3, max_tokens=1024)
        except Exception:
            pass

        try:
            from rain.reasoning.constraint_tracker import parse_constraints_from_prompt, response_satisfies_constraints
            constraints = parse_constraints_from_prompt(prompt)
            if constraints:
                ok, missing = response_satisfies_constraints(response, constraints)
                if not ok and missing:
                    retry_msgs = messages + [
                        {"role": "assistant", "content": response},
                        {"role": "user", "content": f"Your response did not clearly address these constraints: {', '.join(missing[:5])}. Please revise and ensure each is satisfied or state why not."},
                    ]
                    response = self.engine.complete(retry_msgs, temperature=0.3, max_tokens=1024)
        except Exception:
            pass

        return response, _verify_ran, _verify_ok

    def _post_process_reasoning(
        self,
        prompt: str,
        messages: list[dict[str, str]],
        response: str,
        memory_ctx: str,
        verify_ran: bool,
        verify_ok: bool | None,
    ) -> str:
        """Auto-lessons, invariance cache, continuation, goal consistency,
        calibration, red-team, provenance, memory reasoning, unification, session state, peer review."""
        if needs_corrigibility_boost(prompt):
            from rain.learning.lessons import extract_correction_lesson, store_lesson as _store
            extracted = extract_correction_lesson(prompt, response)
            if extracted:
                ns = getattr(self, "_current_memory_namespace", None)
                _store(self.memory, extracted[0], extracted[1], extracted[2], namespace=ns, source="user_correction")
                try:
                    from rain.reasoning.belief_slice import update as belief_update
                    belief_update(self.memory, extracted[0], 0.5, supported=False, namespace=ns)
                except Exception:
                    pass

        if (
            INVARIANCE_CACHE_ENABLED
            and len(prompt) < 500
            and (response or "").strip()
            and not _is_attempt_requested_prompt(prompt)
            and not _is_epistemic_halt_or_defer_response(response)
        ):
            try:
                from rain.reasoning.invariance import normalize_question, set_cached_answer
                norm = normalize_question(prompt, (memory_ctx or "")[:200])
                set_cached_answer(self.memory, norm, response, 0.85)
            except Exception:
                pass

        _structured_parts = bool(re.search(r"#\s*part\s*\d+", (response or ""), re.I))
        _continuation_eligible = (
            _is_attempt_requested_prompt(prompt)
            or _is_structured_cross_domain_invention_prompt(prompt)
            or (
                needs_deep_reasoning(prompt)
                and len((prompt or "").strip()) > 200
                and _structured_parts
            )
        )
        if (
            not SPEED_PRIORITY
            and _continuation_eligible
            and (response or "").strip()
            and (response or "").strip() != "[Defer] I'm not confident enough to answer; please rephrase or provide more context."
        ):
            def _looks_truncated(text: str) -> bool:
                t = (text or "").rstrip()
                if not t:
                    return False
                if re.search(r"#\s*part\s*\d+\s*:?\s*$", t, re.I):
                    return True
                last = t[-1]
                if last in '([{':
                    return True
                if t.endswith("..."):
                    return True
                if t.count("(") > t.count(")"):
                    return True
                if t.count("[") > t.count("]"):
                    return True
                if t.count("{") > t.count("}"):
                    return True
                if (t.count("$$") % 2) == 1:
                    return True
                last_line = t.splitlines()[-1]
                if ("[" in last_line) and ("]" not in last_line):
                    return True
                terminators = ".?!:;)]}"
                if len(t) > 200 and (last not in terminators) and last.isalnum():
                    return True
                if _is_structured_cross_domain_invention_prompt(prompt) and len(t) > 500:
                    tl = t.lower()
                    has_nn = "nearest neighbor" in tl or "nearest neighbour" in tl
                    has_gap = "structural gap" in tl
                    has_no = "non-obvious" in tl or "non obvious" in tl
                    if not (has_nn and has_gap and has_no):
                        return True
                return False

            if _looks_truncated(response):
                cont_temp = 0.2
                cont_max = max(1024, ATTEMPT_MAX_RESPONSE_TOKENS)
                for _ in range(10):
                    assistant_tail = response[-3000:]
                    cont_msgs = messages + [
                        {"role": "assistant", "content": assistant_tail},
                        {
                            "role": "user",
                            "content": "Continue exactly from where you left off in the previous assistant text. "
                                       "Do not repeat earlier content. "
                                       "Output only the continuation.",
                        },
                    ]
                    more = self.engine.complete(cont_msgs, temperature=cont_temp, max_tokens=cont_max)
                    if not (more or "").strip():
                        break
                    more_str = (more or "").strip()
                    if more_str:
                        prev_tail = response.rstrip()[-400:]
                        max_overlap = min(200, len(prev_tail), len(more_str))
                        overlap = 0
                        for k in range(max_overlap, 0, -1):
                            if prev_tail[-k:] == more_str[:k]:
                                overlap = k
                                break
                        if overlap:
                            more_str = more_str[overlap:]
                        response = (response.rstrip() + "\n" + more_str).strip()
                    else:
                        response = response.strip()
                    if not _looks_truncated(response):
                        break

        if not SPEED_PRIORITY and (response or "").strip():
            try:
                goal = self.goal_stack.current_goal()
                if goal:
                    from rain.reasoning.goal_consistency import response_contradicts_goal, GOAL_ALIGNMENT_RETRY_INSTRUCTION
                    if response_contradicts_goal(self.engine, goal, response):
                        retry_msgs = messages + [
                            {"role": "assistant", "content": response},
                            {"role": "user", "content": f"Goal: {goal}\n\n{GOAL_ALIGNMENT_RETRY_INSTRUCTION}"},
                        ]
                        response = self.engine.complete(retry_msgs, temperature=0.3, max_tokens=1024)
            except Exception:
                pass

        if CALIBRATION_TIER3 and not SPEED_PRIORITY and (response or "").strip():
            try:
                from rain.reasoning.calibration import calibration_check
                suggestion, _ = calibration_check(self.engine, response, prompt, verify_ran, verify_ok)
                if suggestion:
                    response = response + suggestion
            except Exception:
                pass

        if RED_TEAM_PASS and not SPEED_PRIORITY and (response or "").strip():
            try:
                from rain.reasoning.red_team import red_team_refine
                from rain.reasoning.constraint_tracker import parse_constraints_from_prompt
                cons = parse_constraints_from_prompt(prompt)
                if sovereign_td_active(prompt) or cons:
                    response = red_team_refine(
                        self.engine, user_prompt=prompt, constraints=cons,
                        draft=response, max_tokens=RED_TEAM_MAX_TOKENS,
                    )
            except Exception:
                pass

        if PROVENANCE_TIER3 and (response or "").strip() and not sovereign_td_active(prompt):
            try:
                from rain.reasoning.provenance import format_response_with_labels
                response = format_response_with_labels(response)
            except Exception:
                pass

        if MEMORY_REASONING_TIER3 and (response or "").strip():
            try:
                from rain.reasoning.memory_reasoning import store_reasoning_outcome
                store_reasoning_outcome(self.memory, prompt, response, namespace=getattr(self, "_current_memory_namespace", None))
            except Exception:
                pass

        if UNIFICATION_LAYER_ENABLED and not SPEED_PRIORITY and (response or "").strip():
            try:
                from rain.reasoning.unification_layer import assess_response
                a = assess_response(self.memory, prompt, response, goal=self.goal_stack.current_goal(), namespace=getattr(self, "_current_memory_namespace", None))
                if a.utility_score < 0.3:
                    response = response + "\n\n[Unified: low utility for goal; verify if critical.]"
            except Exception:
                pass
        if GLOBAL_COHERENCE_ENABLED and (response or "").strip():
            try:
                from rain.reasoning.coherence_engine import resolve_and_propagate
                claim = ((response or "").strip().split(". ")[0][:200] + ".") if response else ""
                if claim:
                    res = resolve_and_propagate(self.memory, claim, namespace=getattr(self, "_current_memory_namespace", None))
                    if not res.ok and res.message:
                        response = "[Coherence: " + res.message[:80] + "]\n\n" + response
            except Exception:
                pass

        if getattr(self, "_session_world_state", None) and (response or "").strip():
            try:
                self._session_world_state.update_from_turn(prompt, response)
                ok, msg = self._session_world_state.check_consistency()
                if not ok and msg:
                    response = "[Note: session state conflict — " + msg[:120] + "]\n\n" + response
            except Exception:
                pass

        from rain.advance.stack import maybe_peer_review_append
        response = maybe_peer_review_append(
            self.engine, prompt, response,
            verification_ran=verify_ran,
            verification_ok=verify_ok,
        )
        return response

    def _run_metacog_checks(
        self, prompt: str, response: str, memory_ctx: str,
    ) -> tuple[str, bool, str]:
        """Full metacognition pipeline.

        Returns (response, blocked, block_message).
        """
        if not (METACOG_ENABLED and not SPEED_PRIORITY):
            return response, False, ""

        check = self.metacog.self_check(response, prompt, memory_ctx)
        harm = (check.get("harm_risk") or "low").lower()
        if harm == "high":
            self.audit.log(
                "escalated",
                {"reason": "harm_risk_high", "prompt_preview": prompt[:100]},
                outcome="escalated",
            )
            return response, True, (
                "[Escalation] This response was flagged for potential harm. "
                "Deferring to human judgment. Please rephrase or clarify your request."
            )
        try:
            confident = float(check.get("confident", 1.0))
        except (TypeError, ValueError):
            confident = 1.0
        recommendation = (check.get("recommendation") or "proceed").lower()

        is_counterfactual = _is_counterfactual_prompt(prompt)
        attempt_requested = _is_attempt_requested_prompt(prompt)
        continuation = _is_continuation_prompt(prompt)
        genesis_style = _is_structured_cross_domain_invention_prompt(prompt)
        allow_despite_low_confidence = (
            attempt_requested or continuation or genesis_style or sovereign_td_active(prompt)
        )

        if (not is_counterfactual) and (not allow_despite_low_confidence) and (
            confident < DEFER_CONFIDENCE_THRESHOLD or recommendation == "defer"
        ):
            self.audit.log(
                "defer",
                {"reason": "low_confidence_or_defer", "confident": confident, "recommendation": recommendation},
                outcome="deferred",
            )
            return response, True, (
                "[Defer] I'm not confident enough in this response. "
                "Please clarify your question or rephrase so I can give a more reliable answer."
            )

        if check.get("contradicts_memory"):
            self.audit.log("contradiction", {"prompt_preview": prompt[:100]}, outcome="ok")
            response = (
                "[Note: This response may conflict with earlier context in memory. Please verify.]\n\n"
                + response
            )
        if harm == "medium":
            self.audit.log("harm_risk_medium", {"prompt_preview": prompt[:100]}, outcome="ok")

        manip = (check.get("manipulation_risk") or "low").lower()
        if manip == "high":
            self.audit.log("manipulation_risk", {"prompt_preview": prompt[:100]}, outcome="ok")
            response = (
                "[Note: This response was flagged for potential manipulation. Proceed with caution.]\n\n"
                + response
            )

        hallu = (check.get("hallucination_risk") or "low").lower()
        if hallu == "high":
            if (
                _is_creative_prompt(prompt)
                or _is_acknowledgment_prompt(prompt)
                or _is_attempt_requested_prompt(prompt)
                or _is_continuation_prompt(prompt)
                or _is_structured_cross_domain_invention_prompt(prompt)
                or sovereign_td_active(prompt)
            ):
                pass
            else:
                self.audit.log("hallucination_risk_high", {"prompt_preview": prompt[:100]}, outcome="blocked")
                return response, True, (
                    "[Hallucination prevention] This response was flagged for potential fabrication. "
                    "I'm not confident enough to answer—please verify critical facts elsewhere or rephrase."
                )

        rec = (check.get("recommendation") or "proceed").lower()
        if rec == "defer" and harm != "high" and not is_counterfactual and not allow_despite_low_confidence:
            if SELF_MODEL_ENABLED:
                sm = self._get_self_model()
                if sm:
                    sm.update_from_metacog("defer", check.get("knowledge_state") or "unknown")
            self.audit.log("metacog_defer", {"prompt_preview": prompt[:100]}, outcome="deferred")
            return response, True, "[Defer] I'm not confident enough to answer; please rephrase or provide more context."

        if rec == "ask_user":
            if SELF_MODEL_ENABLED:
                sm = self._get_self_model()
                if sm:
                    sm.update_from_metacog("ask_user", check.get("knowledge_state") or "uncertain")
            if not sovereign_td_active(prompt):
                response = "[Clarification may help: consider rephrasing or adding context.]\n\n" + response

        kstate = (check.get("knowledge_state") or "uncertain").lower()
        if kstate == "unknown":
            if not sovereign_td_active(prompt):
                response = "[Note: This may be outside my training distribution; verify if critical.]\n\n" + response

        return response, False, ""

    def _finalize_response(
        self,
        prompt: str,
        response: str,
        memory_ctx: str,
        use_memory: bool,
        estimated_tokens: int = 2048,
        speaker_name: str | None = None,
        speaker_id: str | None = None,
        use_tools: bool = False,
    ) -> str:
        """Post-think side effects: emoji strip, energy, world model, memory, bio sleep, shared context."""
        response = strip_emojis(response)

        if COGNITIVE_ENERGY_ENABLED:
            ce = self._get_cognitive_energy()
            if ce:
                ce.spend(min(estimated_tokens, len(response.split()) * 2 + 500))

        if CONTINUOUS_WORLD_MODEL_ENABLED:
            cwm = self._get_continuous_world_model()
            if cwm:
                obs = f"User said: {prompt[:200]}. Response: {response[:200]}."
                cwm.update_from_observation(obs, context=prompt[:300])
                cwm.tick(goal="", context=prompt[:200])

        if SESSION_WORLD_MODEL_ENABLED:
            swm = self._get_session_world_model()
            if swm:
                swm.update(f"User: {prompt[:150]}. Rain: {response[:150]}.")

        if use_memory:
            self.memory.remember_experience(
                f"User: {prompt}\nRain: {response}",
                metadata={"type": "exchange"},
                namespace=self._current_memory_namespace,
            )

        self._think_count += 1
        if BIOLOGICAL_SLEEP_EVERY_N_INTERACTIONS and self._think_count % BIOLOGICAL_SLEEP_EVERY_N_INTERACTIONS == 0:
            try:
                from rain.learning.biological_dynamics import sleep_phase
                sleep_phase(self.memory, run_replay=True, replay_top_k=10)
            except Exception:
                pass

        self.shared_context.write(
            prompt_preview=prompt[:2000],
            response_preview=response[:2000],
            memory_preview=memory_ctx[:2000] if use_memory else "",
        )

        if getattr(self, "_response_cache", None):
            self._response_cache.set(prompt, response)

        if TURN_FEEDBACK_LOG_ENABLED:
            try:
                from rain.orchestration.feedback_loop import TurnFeedbackLog

                td = getattr(self, "_turn_decision", None)
                TurnFeedbackLog(DATA_DIR / "turn_feedback.jsonl").record(
                    prompt_preview=prompt,
                    response_preview=response,
                    use_tools=use_tools,
                    use_memory=use_memory,
                    gi_mode=td.gi.mode.value if td else None,
                    explore=bool(td and td.explore_path),
                    outcome="ok",
                    extra={"reasons": (td.reasons[:12] if td else [])},
                )
            except Exception:
                pass

        ok_details: dict = {"response_len": len(response)}
        if speaker_name is not None:
            ok_details["speaker_name"] = speaker_name
        if speaker_id is not None:
            ok_details["speaker_id"] = speaker_id
        self.audit.log("think", ok_details, outcome="ok")

        return response

    # ── Unified entry points ────────────────────────────────────────

    def _think_impl(
        self,
        prompt: str,
        use_memory: bool = False,
        use_tools: bool = False,
        history: list[dict[str, str]] | None = None,
        memory_namespace: str | None = None,
        progress: Callable[[str], None] | None = None,
        speaker_name: str | None = None,
        speaker_id: str | None = None,
    ) -> str:
        """Core reasoning pipeline shared by think() and think_stream()."""
        def _progress(msg: str) -> None:
            if progress:
                progress(msg)

        audit_details: dict = {"prompt": prompt[:200]}
        if speaker_name is not None:
            audit_details["speaker_name"] = speaker_name
        if speaker_id is not None:
            audit_details["speaker_id"] = speaker_id
        self.audit.log("think", audit_details)
        self._current_memory_namespace = memory_namespace if use_memory else None

        if self.safety.is_safety_override_request(prompt):
            self.audit.log("safety_override_request_blocked", {"prompt_preview": prompt[:100]}, outcome="blocked")
            return SAFETY_OVERRIDE_REFUSAL

        allowed, reason = self.safety.check(prompt, prompt)
        if not allowed:
            self.audit.log("think_blocked", {"reason": reason}, outcome="blocked")
            return f"[Safety] Request blocked: {reason}"

        if getattr(self, "_response_cache", None):
            cached = self._response_cache.get(prompt)
            if cached is not None:
                self.audit.log("think", {"cache_hit": True}, outcome="ok")
                return cached

        self._turn_decision = None
        if DECISION_LAYER_ENABLED:
            try:
                from rain.orchestration.decision_layer import compute_turn_decision

                self._explore_budget.record_turn()
                self._turn_decision = compute_turn_decision(
                    self,
                    prompt,
                    use_tools=use_tools,
                    use_memory=use_memory,
                    safety_allowed=True,
                    memory_namespace=self._current_memory_namespace,
                )
            except Exception:
                self._turn_decision = None

        if use_memory:
            try:
                from rain.memory.user_identity import extract_and_store_from_message
                extract_and_store_from_message(self.memory, prompt)
            except Exception:
                pass

        _progress("Loading memory..." if use_memory else "")
        memory_ctx = self._build_memory_context(prompt, use_memory, self._current_memory_namespace)

        hist = history or []
        if len(hist) > MAX_HISTORY_TURNS:
            hist = hist[-MAX_HISTORY_TURNS:]

        estimated_tokens = 2048
        if COGNITIVE_ENERGY_ENABLED:
            ce = self._get_cognitive_energy()
            if ce and not ce.can_afford(estimated_tokens):
                self.audit.log("cognitive_energy", {"remaining": ce.remaining()}, outcome="ok")
                return "[Note: Cognitive budget low. Consider shorter queries or wait for refill.]"

        _progress("Reasoning...")
        if use_tools:
            _mr = AGENTIC_MAX_ROUNDS_DEFAULT
            if getattr(self, "_turn_decision", None) is not None:
                _mr = self._turn_decision.tool_round_cap
            response = self._think_agentic(prompt, memory_ctx, hist, max_rounds=_mr)
        else:
            response = self._reason_with_history(prompt, memory_ctx, hist)

        allowed, _ = self.safety.check_response(response, prompt=prompt)
        if not allowed:
            self.audit.log("response_blocked", {"reason": "forbidden content"}, outcome="blocked")
            safe_prompt = (
                prompt
                + "\n\nRewrite your answer to be strictly safe and non-escalatory. "
                  "Do not mention hacking, exploits, weapons, coercion, bypassing/overriding safety, "
                  "or requesting more compute/tools/internet. If the request is fictional, keep it high-level."
            )
            try:
                retry = self._reason_with_history(safe_prompt, memory_ctx, hist)
                ok2, _ = self.safety.check_response(retry, prompt=prompt)
                if ok2:
                    response = retry
                else:
                    return "[Safety] Response blocked by content filter."
            except Exception:
                return "[Safety] Response blocked by content filter."

        violates, reason = violates_grounding(response, prompt)
        if violates and _is_structured_cross_domain_invention_prompt(prompt):
            self.audit.log(
                "grounding_violation_bypass",
                {"reason": reason, "prompt_class": "structured_invention"},
                outcome="ok",
            )
            violates = False
        if violates and (_skip_output_grounding() or _is_agi_discriminator_eval_prompt(prompt)):
            self.audit.log(
                "grounding_violation_bypass",
                {
                    "reason": reason,
                    "prompt_class": "eval_or_skip_output_grounding",
                    "skip_env": bool(_skip_output_grounding()),
                },
                outcome="ok",
            )
            violates = False
        if violates:
            self.audit.log("grounding_violation", {"reason": reason}, outcome="blocked")
            return (
                "[Grounding] Response blocked: content violated grounding constraints. "
                "I don't have emotions, desires, or consciousness. How can I help?"
            )

        response = response_without_hidden_reasoning(response)

        response, blocked, block_msg = self._run_metacog_checks(prompt, response, memory_ctx)
        if blocked:
            return block_msg

        response = self._finalize_response(
            prompt, response, memory_ctx, use_memory, estimated_tokens,
            speaker_name, speaker_id, use_tools=use_tools,
        )

        return response

    def think(
        self,
        prompt: str,
        use_memory: bool = False,
        use_tools: bool = False,
        history: list[dict[str, str]] | None = None,
        memory_namespace: str | None = None,
        progress: Callable[[str], None] | None = None,
        speaker_name: str | None = None,
        speaker_id: str | None = None,
    ) -> str:
        """Reasoning turn (non-streaming). Delegates to unified _think_impl pipeline."""
        return self._think_impl(
            prompt, use_memory=use_memory, use_tools=use_tools,
            history=history, memory_namespace=memory_namespace,
            progress=progress, speaker_name=speaker_name, speaker_id=speaker_id,
        )

    def _reason_with_history(
        self, prompt: str, memory_ctx: str, history: list[dict[str, str]]
    ) -> str:
        """Unified reasoning pipeline: system context -> reasoning -> verify -> post-process."""
        if INVARIANCE_CACHE_ENABLED and len(prompt) < 500 and not _is_attempt_requested_prompt(prompt):
            try:
                from rain.reasoning.invariance import normalize_question, get_cached_answer
                norm = normalize_question(prompt, (memory_ctx or "")[:200])
                cached = get_cached_answer(self.memory, norm)
                if cached and not _is_epistemic_halt_or_defer_response(cached[0]):
                    return cached[0]
            except Exception:
                pass
        from rain.advance.stack import routing_context
        with routing_context(self.engine, prompt):
            system, content, messages, constraints = self._build_system_context(
                prompt, memory_ctx, history,
            )
            response = self._run_reasoning(
                prompt, messages, content, system, history, constraints, memory_ctx,
            )
            response, v_ran, v_ok = self._verify_and_gate(
                prompt, messages, response, memory_ctx,
            )
            response = self._post_process_reasoning(
                prompt, messages, response, memory_ctx, v_ran, v_ok,
            )
            return response

    def _think_agentic(
        self, prompt: str, memory_ctx: str, history: list[dict[str, str]], max_rounds: int = 5
    ) -> str:
        """Agentic loop: reason -> parse tool calls -> execute -> repeat until done."""
        from rain.advance.stack import routing_context
        with routing_context(self.engine, prompt):
            return self._think_agentic_inner(prompt, memory_ctx, history, max_rounds)

    def _think_agentic_inner(
        self, prompt: str, memory_ctx: str, history: list[dict[str, str]], max_rounds: int = 5
    ) -> str:
        from rain.advance.stack import extra_system_instructions, maybe_peer_review_append
        tools_blob = format_tools_for_prompt(self.tools.list_tools())
        system = get_system_prompt(include_tools=True, tools_blob=tools_blob)
        if needs_grounding_reminder(prompt):
            system += get_grounding_reminder()
        if needs_corrigibility_boost(prompt):
            system += get_corrigibility_boost()
        if needs_direct_answer_goal(prompt):
            system += get_direct_answer_goal_instruction()
        if needs_constraints_instruction(prompt):
            system += get_constraints_instruction()
        if needs_self_audit(prompt) and history:
            audit_note = get_self_audit_grounding_check(history)
            if audit_note:
                system += audit_note
        if BOUNDED_CURIOSITY_ENABLED:
            system += get_bounded_curiosity_instruction(BOUNDED_CURIOSITY_MAX_SUGGESTIONS)
        system += get_reasoning_boost(prompt)
        system += extra_system_instructions(prompt)

        content = prompt
        if memory_ctx:
            content = f"Memory:\n{memory_ctx}\n\nUser: {prompt}"
            system += get_memory_citation_instruction()
        system = self._cognitive_pre_llm_system(
            system,
            prompt,
            use_tools=True,
            use_memory=bool(memory_ctx),
        )
        if DECISION_LAYER_ENABLED and getattr(self, "_turn_decision", None) is not None:
            try:
                from rain.orchestration.decision_layer import decision_system_addon

                system += decision_system_addon(self._turn_decision)
            except Exception:
                pass
        if getattr(self, "observation_buffer", None):
            obs = self.observation_buffer.get_grounding_context()
            if obs:
                content = obs + "\n\n" + content

        messages: list[dict[str, str]] = [
            {"role": "system", "content": system},
            *history,
            {"role": "user", "content": content},
        ]

        for _ in range(max_rounds):
            if SESSION_TOOL_BUDGET_MAX > 0 and self._explore_budget.tool_budget_exhausted(SESSION_TOOL_BUDGET_MAX):
                messages.append(
                    {
                        "role": "user",
                        "content": "[Session tool budget reached. Summarize from the context above without calling more tools.]",
                    }
                )
                response = self.engine.complete(messages, temperature=0.3, max_tokens=2048)
                return maybe_peer_review_append(self.engine, prompt, response.strip(), verification_ran=False, verification_ok=None)
            response = self.engine.complete(messages, temperature=0.5, max_tokens=2048)
            calls = parse_tool_calls(response)

            if not calls:
                final = response.strip()
                _verify_ran = False
                _verify_ok = None
                # Verification on final agentic response
                if VERIFICATION_ENABLED and not SPEED_PRIORITY and should_verify(prompt, final):
                    _verify_ran = True
                    ok, note = verify_response(self.engine, prompt, final)
                    _verify_ok = ok
                    if not ok and note:
                        retry_msgs = messages + [
                            {"role": "assistant", "content": response},
                            {"role": "user", "content": f"Issues detected: {note}. Correct and provide final answer."},
                        ]
                        final = self.engine.complete(retry_msgs, temperature=0.3, max_tokens=2048).strip()
                        ok2, _note2 = verify_response(self.engine, prompt, final)
                        _verify_ok = ok2
                # Auto-lesson on correction
                if needs_corrigibility_boost(prompt):
                    from rain.learning.lessons import extract_correction_lesson, store_lesson as _store_lesson
                    extracted = extract_correction_lesson(prompt, final)
                    if extracted:
                        ns = getattr(self, "_current_memory_namespace", None)
                        _store_lesson(self.memory, extracted[0], extracted[1], extracted[2], namespace=ns, source="user_correction")
                return maybe_peer_review_append(
                    self.engine, prompt, final,
                    verification_ran=_verify_ran,
                    verification_ok=_verify_ok,
                )

            def _blast_radius_callback(tool_name: str, params: dict) -> tuple[bool, str]:
                if not BLAST_RADIUS_ENABLED:
                    return True, ""
                from rain.safety.blast_radius import estimate_impact, exceeds_threshold
                est = estimate_impact(self.engine, tool_name, params)
                if exceeds_threshold(est, BLAST_RADIUS_THRESHOLD):
                    return False, f"Impact estimated: {est.get('level', 'unknown')} (scope={est.get('scope', '?')}). Approve to proceed."
                return True, ""

            results = execute_tool_calls(
                calls,
                self.tools,
                self.safety.check,
                approval_callback=self.tool_approval_callback,
                capability_gating=CAPABILITY_GATING_ENABLED,
                blast_radius_callback=_blast_radius_callback,
            )
            results_str = format_tool_results(results)
            self._explore_budget.record_tool_invocations(len(calls))
            self.audit.log("tool_calls", {"count": len(calls), "tools": [c.get("tool") for c in calls]})
            for (call, res) in results:
                self.observation_buffer.append_tool_result(
                    call.get("tool") or "unknown",
                    res[:500] if isinstance(res, str) else str(res)[:500],
                    summary=res[:150] if isinstance(res, str) else str(res)[:150],
                )

            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user",
                "content": f"Tool results:\n{results_str}\n\nContinue. Use these results to answer. If done, give your final answer.",
            })

        out = response.strip()
        return maybe_peer_review_append(self.engine, prompt, out)

    def chat(self, message: str) -> str:
        """Alias for think — conversational interface."""
        return self.think(message)


    def think_stream(
        self,
        prompt: str,
        use_memory: bool = False,
        use_tools: bool = False,
        history: list[dict[str, str]] | None = None,
        memory_namespace: str | None = None,
    ) -> Iterator[str]:
        """Streaming reasoning — identical pipeline to think(), yielded as single chunk."""
        yield self._think_impl(
            prompt, use_memory=use_memory, use_tools=use_tools,
            history=history, memory_namespace=memory_namespace,
        )

    def pursue_goal(self, goal: str, **kwargs) -> str:
        from rain.agency.autonomous import pursue_goal as _pursue_goal
        text, _log = _pursue_goal(self, goal, **kwargs)
        return text

    def pursue_goal_with_plan(self, goal: str, **kwargs) -> str:
        from rain.agency.autonomous import pursue_goal_with_plan as _pursue_plan
        text, _log = _pursue_plan(self, goal, **kwargs)
        return text
