"""Advance stack: no-op when disabled; routing restores model."""

import importlib

from rain.core.engine import CoreEngine


def test_routing_context_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("RAIN_ADVANCE_STACK", "false")
    import rain.config as cfg
    importlib.reload(cfg)

    from rain.advance.stack import routing_context

    eng = CoreEngine()
    before = eng.model
    with routing_context(eng, "hello"):
        assert eng.model == before


def test_begin_routing_sets_strong_when_complex(monkeypatch):
    monkeypatch.setenv("RAIN_ADVANCE_STACK", "true")
    monkeypatch.setenv("RAIN_ADVANCE_DRAFT_MODEL", "draft-model-x")
    monkeypatch.setenv("RAIN_ADVANCE_STRONG_MODEL", "strong-model-y")
    import rain.config as cfg
    importlib.reload(cfg)

    from rain.advance.stack import begin_routing, end_routing

    eng = CoreEngine()
    eng.model = "default-z"
    # "prove " (+2) + "step-by-step" (+2) => complexity >= 3 => strong model
    prev = begin_routing(eng, "prove the Riemann hypothesis step-by-step")
    assert prev == "default-z"
    assert eng.model == "strong-model-y"
    end_routing(eng, prev)
    assert eng.model == "default-z"


def test_begin_routing_draft_for_trivial_prompt(monkeypatch):
    monkeypatch.setenv("RAIN_ADVANCE_STACK", "true")
    monkeypatch.setenv("RAIN_ADVANCE_DRAFT_MODEL", "draft-model-x")
    monkeypatch.setenv("RAIN_ADVANCE_STRONG_MODEL", "strong-model-y")
    import rain.config as cfg
    importlib.reload(cfg)

    from rain.advance.stack import begin_routing, end_routing

    eng = CoreEngine()
    eng.model = "default-z"
    prev = begin_routing(eng, "hi")
    assert prev == "default-z"
    assert eng.model == "draft-model-x"
    end_routing(eng, prev)
