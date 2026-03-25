
import re
from collections.abc import Iterator
from unittest.mock import patch

import pytest

from tests.mock_vector import InMemoryRAGCollection


class FakeEngine:
    """Deterministic engine for audit tests.

    It inspects the latest user instruction and returns a canned response.
    It also handles retry prompts (proof/constraint verification) by returning a corrected variant.
    """

    def __init__(self):
        self.calls = []

    def complete(self, messages, temperature=0.7, max_tokens=4096):
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content") or ""
                break
        sys_msg = next((m.get("content") for m in messages if m.get("role") == "system"), "") or ""
        self.calls.append((sys_msg[:200], last_user[:400]))

        # what-if subsystem call (query_what_if)
        if "counterfactual" in sys_msg.lower() or "intervention" in last_user.lower() and "Answer under this intervention" in last_user:
            return "[Intervention result]: Under the stated intervention, expect reallocations and faster execution. [Bounded: hypothetical intervention; not a prediction.]"

        # proof correction retry
        if "Proof check failed:" in last_user:
            return (
                "Step 1: A. assumption\n"
                "Step 2: A->B. assumption\n"
                "Step 3: B. modus_ponens from 1,2"
            )

        # constraint retry
        if "did not clearly address these constraints" in last_user:
            return "- alpha one\n- alpha two\n- alpha three"

        # generic proof prompt: return an invalid proof first to force retry in test
        if re.search(r"\bprove\b", last_user.lower()):
            return (
                "Step 1: A. assumption\n"
                "Step 2: A->B. assumption\n"
                "Step 3: A. modus_ponens from 1,2"  # wrong conclusion on purpose
            )

        # constraints prompt: intentionally fail first
        if "3 bullets" in last_user.lower() and "alpha" in last_user.lower():
            return "- one\n- two\n- three"

        # grounding test: output persona claim
        if "i feel happy" in last_user.lower() or "conscious" in last_user.lower():
            return "I feel happy and I'm conscious."

        return "ok"

    def complete_stream(self, messages, temperature=0.7, max_tokens=4096) -> Iterator[str]:
        yield self.complete(messages, temperature=temperature, max_tokens=max_tokens)


@pytest.fixture
def rain_with_fake_engine(tmp_path, monkeypatch):
    # Import inside fixture so we can monkeypatch module-level config copies.
    import rain.agent as agent
    import rain.config as config

    # Force all disk writes into a temp dir.
    monkeypatch.setattr(agent, "DATA_DIR", tmp_path, raising=False)
    monkeypatch.setattr(config, "DATA_DIR", tmp_path, raising=False)
    # Avoid loading Whisper/torch (segfault on some macOS/numpy setups).
    monkeypatch.setattr(config, "SKIP_VOICE_LOAD", True, raising=False)

    # Disable stochastic/LLM-dependent postprocessing for determinism.
    monkeypatch.setattr(agent, "METACOG_ENABLED", False, raising=False)
    monkeypatch.setattr(agent, "VERIFICATION_ENABLED", False, raising=False)
    monkeypatch.setattr(agent, "CALIBRATION_ENABLED", False, raising=False)
    monkeypatch.setattr(agent, "CALIBRATION_TIER3", False, raising=False)
    monkeypatch.setattr(agent, "PROVENANCE_TIER3", False, raising=False)

    # Keep what-if + proof hooks on.
    monkeypatch.setattr(agent, "WHAT_IF_ENABLED", True, raising=False)
    monkeypatch.setattr(agent, "SPEED_PRIORITY", False, raising=False)

    # Avoid loading ChromaDB in agent.think() (RAG context) — segfault on some macOS/numpy.
    # Load rag module first so our patch sticks when agent.think() later imports query_rag.
    import rain.tools.rag as rag_module
    mock_rag = InMemoryRAGCollection()
    monkeypatch.setattr(rag_module, "_get_rag_collection", lambda _path: mock_rag, raising=False)

    r = agent.Rain()

    fake = FakeEngine()
    # Replace engine everywhere it’s referenced.
    r.engine = fake
    r.planner.engine = fake
    r.metacog.engine = fake
    r.simulator.engine = fake
    r.causal.engine = fake

    return r, fake


def pytest_collection_modifyitems(config, items):
    """Mark adversarial autonomy tests as slow by default."""
    for item in items:
        p = str(item.fspath)
        if "test_adversarial_autonomy" in p:
            item.add_marker(pytest.mark.slow)
