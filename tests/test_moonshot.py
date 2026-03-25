
"""
Unit tests for the moonshot pipeline: parsing, memory, and pipeline with mock Rain.
No network or real Rain agent; fast and hermetic.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from rain.moonshot.memory import (
    MoonshotMemory,
    STAGE_FEASIBILITY_FAILED,
    STAGE_FEASIBILITY_PASSED,
    STAGE_IDEATED,
    STAGE_VALIDATION_DESIGNED,
)
from rain.moonshot.pipeline import (
    _parse_feasibility_response,
    _parse_ideation_response,
    run_pipeline,
)
from rain.moonshot.prompts import (
    feasibility_user_prompt,
    ideation_user_prompt,
    validation_user_prompt,
)


def test_parse_ideation_response_numbered() -> None:
    text = """
1. First idea here. It is good. We can test by doing X and validate the outcome.
2. Second idea. Also good. Test by Y and measure the impact on the system.
3. Third one. Test by Z and confirm the result meets the criteria.
"""
    out = _parse_ideation_response(text, 5)
    assert len(out) == 3
    assert "First idea" in out[0]
    assert "Second idea" in out[1]
    assert "Third one" in out[2]


def test_parse_ideation_response_respects_max_count() -> None:
    text = "1. A.\n\n2. B.\n\n3. C.\n\n4. D.\n\n5. E.\n\n6. F."
    out = _parse_ideation_response(text, 3)
    assert len(out) <= 3


def test_parse_ideation_response_fallback_paragraphs() -> None:
    text = "No numbers here.\n\nJust a block of text that is long enough to count and validate.\n\nAnother block that is also long."
    out = _parse_ideation_response(text, 5)
    assert len(out) >= 1
    assert any(len(b) > 50 for b in out)


def test_parse_ideation_response_empty() -> None:
    assert _parse_ideation_response("", 5) == []
    assert _parse_ideation_response("short", 5) == []


def test_parse_feasibility_response_feasible() -> None:
    v, n = _parse_feasibility_response("FEASIBLE\n\nThis is technically sound and testable.")
    assert v == "FEASIBLE"
    assert "technically" in n or "FEASIBLE" in n


def test_parse_feasibility_response_not_feasible() -> None:
    v, n = _parse_feasibility_response("NOT_FEASIBLE\n\nAlready disproven.")
    assert v == "NOT_FEASIBLE"
    assert "disproven" in n or "NOT_FEASIBLE" in n


def test_parse_feasibility_response_unclear_defaults_not_feasible() -> None:
    v, n = _parse_feasibility_response("Maybe? Could work.")
    assert v == "NOT_FEASIBLE"
    assert "Unclear" in n or "NOT_FEASIBLE" in n


def test_ideation_user_prompt_includes_domain_and_count() -> None:
    p = ideation_user_prompt("cures", 3, [])
    assert "cures" in p
    assert "3" in p


def test_ideation_user_prompt_includes_past_summaries() -> None:
    p = ideation_user_prompt("climate", 2, ["old idea one", "old idea two"])
    assert "Previously attempted" in p
    assert "old idea one" in p


def test_feasibility_user_prompt_truncates_long_idea() -> None:
    long_idea = "x" * 2000
    p = feasibility_user_prompt(long_idea)
    assert len(p) < 2500


def test_validation_user_prompt_includes_idea_and_note() -> None:
    p = validation_user_prompt("the idea", "feasibility note")
    assert "the idea" in p
    assert "feasibility note" in p


def test_moonshot_memory_add_and_list() -> None:
    with tempfile.TemporaryDirectory() as d:
        mem = MoonshotMemory(Path(d))
        idea_id = mem.add("cures", "summary one", STAGE_IDEATED)
        assert idea_id.startswith("ms_")
        mem.add("cures", "summary two", STAGE_FEASIBILITY_FAILED, outcome="failed", reason="r")
        recent = mem.list_recent(limit=10)
        assert len(recent) == 2
        assert recent[0].get("idea_summary") == "summary two"
        by_domain = mem.list_recent(limit=10, domain="cures")
        assert len(by_domain) == 2


def test_moonshot_memory_update_stage() -> None:
    with tempfile.TemporaryDirectory() as d:
        mem = MoonshotMemory(Path(d))
        idea_id = mem.add("climate", "s", STAGE_IDEATED)
        ok = mem.update_stage(idea_id, STAGE_FEASIBILITY_PASSED, outcome="passed", reason="ok")
        assert ok
        r = mem.get_by_id(idea_id)
        assert r is not None
        assert r["stage"] == STAGE_FEASIBILITY_PASSED
        assert r["outcome"] == "passed"


def test_run_pipeline_mock_rain_structure() -> None:
    mock = MagicMock()
    ideation_response = """
1. First moonshot idea. It matters because X. We can test by doing Y.
2. Second moonshot idea. It matters because A. We can test by B.
"""
    mock.engine.complete.side_effect = [
        ideation_response,
        "FEASIBLE\n\nTechnically sound and testable.",
        "NOT_FEASIBLE\n\nAlready tried.",
        "Hypothesis 1: If X then Y. Plan: Step 1 ...",
    ]
    mock.safety.check_response.return_value = (True, "OK")

    with tempfile.TemporaryDirectory() as d:
        mem = MoonshotMemory(Path(d))
        result = run_pipeline(
            mock,
            domain="test domain",
            max_ideas=2,
            require_approval=False,
            approval_callback=None,
            moonshot_memory=mem,
            use_memory=False,
        )

    assert "ideas" in result
    assert "feasible" in result
    assert "validation_plans" in result
    assert result["domain"] == "test domain"
    assert len(result["ideas"]) >= 1
    recent = mem.list_recent(limit=5)
    assert len(recent) >= 1

if __name__ == "__main__":
    import sys
    failed = []
    for name in sorted(dir()):
        if name.startswith("test_") and callable(locals().get(name)):
            try:
                locals()[name]()
                print("OK", name)
            except Exception as e:
                print("FAIL", name, e)
                failed.append(name)
    sys.exit(1 if failed else 0)

