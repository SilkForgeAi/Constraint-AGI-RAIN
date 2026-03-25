"""Persisted multi-step task state for cross-session resume.

User-initiated only: goal and plan are saved when a plan-driven pursuit runs;
resume is explicitly requested (e.g. --resume). No self-persisting agent goals.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rain.config import DATA_DIR

PERSISTENT_TASK_FILE = DATA_DIR / "persistent_task.json"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"


def save_persistent_task(
    goal: str,
    steps: list[dict[str, Any]],
    current_step_index: int,
    step_log: list[str],
    status: str = STATUS_IN_PROGRESS,
    history: list[dict[str, str]] | None = None,
) -> None:
    """Write current task state to disk. Call after each step and on start."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "goal": goal,
        "steps": steps,
        "current_step_index": current_step_index,
        "step_log": step_log,
        "status": status,
        "history": (history or [])[-20:],
    }
    from datetime import datetime, timezone
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    Path(PERSISTENT_TASK_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(PERSISTENT_TASK_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def load_persistent_task() -> dict[str, Any] | None:
    """Load task state from disk. Returns None if missing or invalid."""
    path = Path(PERSISTENT_TASK_FILE)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or "goal" not in data or "steps" not in data:
            return None
        return data
    except Exception:
        return None


def clear_persistent_task() -> None:
    """Remove persisted task (e.g. when goal is completed)."""
    path = Path(PERSISTENT_TASK_FILE)
    if path.exists():
        path.unlink()
