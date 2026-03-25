"""List directory tool — allowlist under RAIN_ROOT and DATA_DIR only; no parent traversal. Gated by RAIN_LIST_DIR_ENABLED."""

from __future__ import annotations

from pathlib import Path


def _resolve_allowed(path: Path, allowed_dirs: list[Path]) -> Path | None:
    """Resolve path; return None if not under any allowed_dir."""
    try:
        resolved = path.resolve()
    except Exception:
        return None
    for base in allowed_dirs:
        try:
            base_resolved = base.resolve()
            if resolved == base_resolved or resolved.is_relative_to(base_resolved):
                return resolved
        except Exception:
            continue
    return None


def list_dir(relative_path: str = "", base_path: Path | None = None) -> str:
    """
    List directory contents (project or data dir only). Read-only.
    relative_path: e.g. '' for root, 'docs' for docs/, 'data' for data/.
    """
    from rain.config import DATA_DIR, LIST_DIR_ENABLED, RAIN_ROOT

    if not LIST_DIR_ENABLED:
        return "List directory is disabled. Set RAIN_LIST_DIR_ENABLED=true to enable."

    if ".." in (relative_path or "") or (relative_path or "").strip().startswith("/"):
        return "Error: Path must be relative and not use '..'."

    base_path = base_path or RAIN_ROOT
    allowed_dirs = [RAIN_ROOT, DATA_DIR]
    path = (base_path / (relative_path or ".").strip().lstrip("/")).resolve()

    allowed = _resolve_allowed(path, allowed_dirs)
    if allowed is None:
        return "Error: Path not under allowed directories."

    if not allowed.exists():
        return "Error: Path not found."

    if not allowed.is_dir():
        return "Error: Not a directory."

    try:
        entries = sorted(allowed.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        lines = []
        for p in entries[:200]:  # cap entries
            name = p.name
            if p.is_dir():
                name += "/"
            lines.append(name)
        if len(entries) > 200:
            lines.append(f"... and {len(entries) - 200} more")
        return "\n".join(lines) if lines else "(empty)"
    except Exception as e:
        return f"Error: {str(e)[:150]}"
