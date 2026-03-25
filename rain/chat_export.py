"""Export chat sessions to markdown files."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


def history_to_markdown(history: list[dict[str, str]], title: str = "Rain Chat") -> str:
    """Convert message history to markdown."""
    lines = [f"# {title}", "", f"*Exported {datetime.now().strftime('%Y-%m-%d %H:%M')}*", ""]
    for m in history:
        role = m.get("role", "")
        content = m.get("content", "").strip()
        if role == "user":
            lines.append(f"**You:** {content}")
        elif role == "assistant":
            lines.append(f"**Rain:** {content}")
        lines.append("")
    return "\n".join(lines).rstrip()


def save_session(
    history: list[dict[str, str]],
    base_path: Path,
    prefix: str = "chat",
) -> Path:
    """Save session to data/conversations/YYYY-MM-DD_HH-MM-SS_prefix.md. Returns path."""
    base_path = base_path / "conversations"
    base_path.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = base_path / f"{ts}_{prefix}.md"
    md = history_to_markdown(history)
    path.write_text(md, encoding="utf-8")
    return path
