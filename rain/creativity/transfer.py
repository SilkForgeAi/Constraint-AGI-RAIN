"""
Cross-domain transfer: record lessons from one domain and optionally inject into another.
"""

from __future__ import annotations

import json
from typing import Any

from rain.config import DATA_DIR

TRANSFER_DIR = DATA_DIR / "creativity_transfer"
TRANSFER_FILE = TRANSFER_DIR / "lessons.json"


def _load_lessons() -> list[dict[str, Any]]:
    if not TRANSFER_FILE.exists():
        return []
    try:
        raw = TRANSFER_FILE.read_text(encoding="utf-8")
        return json.loads(raw) if raw.strip() else []
    except Exception:
        return []


def _save_lessons(lessons: list[dict[str, Any]]) -> None:
    TRANSFER_DIR.mkdir(parents=True, exist_ok=True)
    TRANSFER_FILE.write_text(json.dumps(lessons, indent=2), encoding="utf-8")


def record_domain_lesson(domain_from: str, domain_to: str, lesson: str, meta: dict[str, Any] | None = None) -> None:
    lessons = _load_lessons()
    lessons.append({
        "domain_from": (domain_from or "")[:200],
        "domain_to": (domain_to or "")[:200],
        "lesson": (lesson or "")[:2000],
        "meta": dict(meta or {}),
    })
    if len(lessons) > 500:
        lessons = lessons[-500:]
    _save_lessons(lessons)


def get_lessons_for_domain(domain: str, limit: int = 5) -> list[str]:
    lessons = _load_lessons()
    domain_lower = (domain or "").lower()
    applicable = [l for l in lessons if domain_lower in (l.get("domain_to") or "").lower()]
    return [l.get("lesson", "") for l in applicable[-limit:] if l.get("lesson")]


def inject_transfer_context(domain: str) -> str:
    lines = get_lessons_for_domain(domain, limit=3)
    if not lines:
        return ""
    return "\n\nRelevant lessons from other domains:\n" + "\n".join(f"- {s[:400]}" for s in lines)
