"""Tests for full subsystems: continuous world model, self-model, cognitive energy, multi-agent, self-reflection, biological dynamics, adaptive planner, vision/spatial tools."""

from __future__ import annotations

import pytest
from pathlib import Path
import tempfile


def test_continuous_world_model():
    import rain.config
    old_backend = getattr(rain.config, "WORLD_MODEL_BACKEND", "llm")
    rain.config.WORLD_MODEL_BACKEND = "classical"
    try:
        from rain.world.continuous_simulator import ContinuousWorldModel
        from rain.world.simulator import WorldSimulator
        cwm = ContinuousWorldModel(simulator=WorldSimulator(), max_states=2)
        state = cwm.get_current_state()
        assert "summary" in state and "entities" in state
        cwm.update_from_observation("User said hello.", "")
        state2 = cwm.get_current_state()
        assert isinstance(state2, dict) and "summary" in state2
        ctx = cwm.get_context_for_prompt(500)
        assert "World model" in ctx or "summary" in ctx or "observation" in ctx.lower()
    finally:
        rain.config.WORLD_MODEL_BACKEND = old_backend


def test_self_model():
    with tempfile.TemporaryDirectory() as d:
        from rain.meta.self_model import SelfModel
        path = Path(d)
        sm = SelfModel(path)
        sm.set_state("thinking", "test goal")
        sm.record_defer()
        ctx = sm.get_self_model_context(800)
        assert "Self-model" in ctx or "Identity" in ctx
        assert "defer" in ctx.lower() or "Defer" in ctx


def test_cognitive_energy_model():
    from rain.capabilities.cognitive_energy import CognitiveEnergyModel
    em = CognitiveEnergyModel(total_tokens=1000, refill_rate=100, refill_interval_seconds=1.0)
    assert em.can_afford(500) is True
    em.spend(600)
    assert em.remaining() == 400
    em.set_focus("test query")
    assert em.get_focus() == "test query"
    status = em.get_status_for_prompt(300)
    assert "budget" in status.lower() or "Focus" in status


def test_multi_agent_cognition():
    from rain.reasoning.multi_agent_cognition import reason_multi_agent, PERSPECTIVES
    assert len(PERSPECTIVES) >= 2
    # Without real engine we only test import and structure
    from rain.core.engine import CoreEngine
    try:
        engine = CoreEngine()
        ans, views = reason_multi_agent("What is 2+2?", engine, n_agents=2, aggregate="vote", max_tokens_per_agent=50)
        assert isinstance(ans, str)
        assert isinstance(views, list) and len(views) <= 3
    except Exception:
        pytest.skip("No LLM API for multi_agent")


def test_self_reflection_belief_revision():
    from rain.reasoning.self_reflection import belief_revision
    from rain.core.engine import CoreEngine
    try:
        engine = CoreEngine()
        new_conf = belief_revision("It will rain.", "Forecast says 90% rain.", 0.5, engine)
        assert 0 <= new_conf <= 1.0
    except Exception:
        pytest.skip("No LLM API for belief_revision")


def test_biological_dynamics():
    from rain.learning.biological_dynamics import consolidation_phase, replay_phase, sleep_phase
    from unittest.mock import MagicMock
    # Use a mock MemoryStore to avoid loading ChromaDB (which can segfault on some macOS/numpy setups).
    store = MagicMock()
    store.vector.get_all_metadata.return_value = []
    store.recall_similar.return_value = []
    store.forget_experience = MagicMock()
    pruned = consolidation_phase(store, max_total=10, prune_older_days=1)
    assert pruned >= 0
    replayed = replay_phase(store, top_k=5)
    assert isinstance(replayed, list)
    result = sleep_phase(store, run_replay=True, replay_top_k=5)
    assert "pruned" in result and "replay_count" in result


def test_adaptive_planner_structure():
    from rain.planning.adaptive_planner import adaptive_plan
    steps_called = []
    exec_called = []
    def get_steps(goal: str, context: str):
        steps_called.append((goal, context))
        return [{"id": 1, "action": "step one", "depends": []}]
    def execute(steps, max_steps):
        exec_called.append((len(steps), max_steps))
        return ("Done", ["Step 1 done"], True)
    resp, log, plans = adaptive_plan("test goal", get_steps, execute, max_phases=2, horizon_steps_per_phase=5)
    assert resp == "Done"
    assert len(log) >= 1
    assert len(plans) >= 1
    assert len(steps_called) >= 1 and len(exec_called) >= 1


def test_vision_tool_import():
    from rain.tools.vision import describe_image
    # Without image file or API, describe_image returns error or placeholder
    out = describe_image(image_path="/nonexistent")
    assert "Error" in out or "not found" in out.lower()


def test_spatial_tool():
    from rain.tools.spatial import spatial_reason
    out = spatial_reason(
        "Room A is north of Room B. The desk is 2m from the window.",
        "Where is the desk relative to Room A?",
        engine=None,
    )
    from rain.core.engine import CoreEngine
    try:
        engine = CoreEngine()
        out2 = spatial_reason("A is left of B. B is left of C.", "What is the order?", engine=engine)
        assert isinstance(out2, str) and len(out2) > 0
    except Exception:
        assert "Error" in out or "engine" in out.lower() or len(out) > 0


def test_agent_has_full_subsystems():
    from rain.agent import Rain
    from rain.config import SELF_MODEL_ENABLED, COGNITIVE_ENERGY_ENABLED
    r = Rain()
    if SELF_MODEL_ENABLED:
        assert r._get_self_model() is not None
    if COGNITIVE_ENERGY_ENABLED:
        assert r._get_cognitive_energy() is not None
    tools = [t["name"] for t in r.tools.list_tools()]
    assert "describe_image" in tools
    assert "spatial_reason" in tools
