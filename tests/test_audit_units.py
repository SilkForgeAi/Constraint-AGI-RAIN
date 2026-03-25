
from rain.reasoning.unification_layer import assess_response
from rain.reasoning.coherence_engine import resolve_and_propagate
from rain.reasoning.belief_slice import update as belief_update


class DummyMemory:
    def __init__(self, symbolic):
        self.symbolic = symbolic


def test_unification_logic_gate_sets_utility_zero(tmp_path):
    # Use real MemoryStore to satisfy belief_slice update/get paths.
    from rain.memory.store import MemoryStore
    m = MemoryStore(tmp_path)
    prompt = "Prove something"
    response = "Step 1: A. assumption\nStep 2: A->B. assumption\nStep 3: A. modus_ponens from 1,2"  # invalid
    a = assess_response(m, prompt, response, goal="")
    assert a.utility_score == 0.0
    assert "invalid_proof" in a.notes


def test_unification_causality_gate_penalizes(tmp_path):
    from rain.memory.store import MemoryStore
    m = MemoryStore(tmp_path)
    prompt = "What if we had more budget?"
    response = "We should hire faster."  # missing intervention/bounded phrasing
    a = assess_response(m, prompt, response, goal="")
    assert a.utility_score <= 0.5  # penalized by factor 0.4 (exact base varies)


def test_coherence_engine_detects_contradiction_and_updates(tmp_path):
    from rain.memory.store import MemoryStore
    m = MemoryStore(tmp_path)

    # Seed an existing belief
    belief_update(m, "the server is running", 0.9, supported=True, namespace="test")

    # Now add contradictory claim
    res = resolve_and_propagate(m, "the server is not running", namespace="test")
    assert res.changed is True
    assert res.ok is False or res.message == "ok"
