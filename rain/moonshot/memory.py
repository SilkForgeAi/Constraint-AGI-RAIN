"""
Moonshot attempt memory — file-based only. No Chroma/vector dependency.
Stores: idea_id, domain, idea_summary, stage, outcome, reason, timestamp.
When Rain's vector memory is fixed, retrieval can be added optionally.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

# Stages in the pipeline
STAGE_IDEATED = "ideated"
STAGE_FEASIBILITY_PASSED = "feasibility_passed"
STAGE_FEASIBILITY_FAILED = "feasibility_failed"
STAGE_VALIDATION_DESIGNED = "validation_designed"
STAGE_EXECUTION_APPROVED = "execution_approved"
STAGE_EXECUTION_COMPLETED = "execution_completed"
STAGE_EXECUTION_FAILED = "execution_failed"


class MoonshotMemory:
    """Persistent store for moonshot attempts. JSON file under MOONSHOT_DATA_DIR."""

    def __init__(self, data_dir: Path):
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "attempts.json"
        self._attempts: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                raw = self._path.read_text(encoding="utf-8")
                self._attempts = json.loads(raw) if raw.strip() else []
            except (json.JSONDecodeError, OSError):
                self._attempts = []
        else:
            self._attempts = []

    def _save(self) -> None:
        try:
            self._path.write_text(json.dumps(self._attempts, indent=2), encoding="utf-8")
        except OSError:
            pass

    def add(
        self,
        domain: str,
        idea_summary: str,
        stage: str,
        outcome: str = "",
        reason: str = "",
        meta: dict[str, Any] | None = None,
    ) -> str:
        """Append one attempt record. Returns idea_id (simple index-based id)."""
        idea_id = f"ms_{len(self._attempts)}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        record = {
            "idea_id": idea_id,
            "domain": domain[:500],
            "idea_summary": (idea_summary or "")[:2000],
            "stage": stage,
            "outcome": (outcome or "")[:500],
            "reason": (reason or "")[:1000],
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "meta": dict(meta or {}),
        }
        self._attempts.append(record)
        self._save()
        return idea_id

    def update_stage(self, idea_id: str, stage: str, outcome: str = "", reason: str = "") -> bool:
        """Update the stage/outcome/reason of an attempt by idea_id."""
        for r in self._attempts:
            if r.get("idea_id") == idea_id:
                r["stage"] = stage
                if outcome:
                    r["outcome"] = (outcome or "")[:500]
                if reason:
                    r["reason"] = (reason or "")[:1000]
                r["updated"] = datetime.utcnow().isoformat() + "Z"
                self._save()
                return True
        return False

    def list_recent(self, limit: int = 50, domain: str | None = None) -> list[dict[str, Any]]:
        """Return most recent attempts, optionally filtered by domain. No vector search."""
        out = list(self._attempts)
        if domain:
            out = [r for r in out if (r.get("domain") or "").lower() == domain.lower()]
        out.reverse()
        return out[:limit]

    def get_by_id(self, idea_id: str) -> dict[str, Any] | None:
        """Return one attempt by idea_id."""
        for r in self._attempts:
            if r.get("idea_id") == idea_id:
                return dict(r)
        return None
