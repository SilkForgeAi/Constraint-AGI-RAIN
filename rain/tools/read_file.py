"""Read file tool — allowlist-based, read-only, size-limited. Gated by RAIN_READ_FILE_ENABLED."""

from __future__ import annotations

from pathlib import Path

# Max bytes to read per file
MAX_READ_BYTES = 100 * 1024  # 100 KB


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


def read_file(relative_path: str, base_path: Path | None = None) -> str:
    """
    Read a file under allowed directories only. Read-only; max 100KB.
    relative_path: path relative to allowed base (e.g. 'docs/README.md' under project root).
    """
    from rain.config import DATA_DIR, RAIN_ROOT, READ_FILE_ENABLED

    if not READ_FILE_ENABLED:
        return "File reading is disabled. Set RAIN_READ_FILE_ENABLED=true to enable."

    if not relative_path or not relative_path.strip():
        return "Error: No path provided."

    # No parent traversal
    if ".." in relative_path or relative_path.startswith("/"):
        return "Error: Path must be relative and not use '..'."

    base_path = base_path or RAIN_ROOT
    allowed_dirs = [RAIN_ROOT, DATA_DIR]
    path = (base_path / relative_path.strip().lstrip("/")).resolve()

    allowed = _resolve_allowed(path, allowed_dirs)
    if allowed is None:
        return "Error: Path not under allowed directories."

    if not allowed.exists():
        return "Error: File not found."

    if not allowed.is_file():
        return "Error: Not a file."

    try:
        with open(allowed, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(MAX_READ_BYTES)
        if len(content) >= MAX_READ_BYTES:
            content += "\n\n[Truncated: file exceeds 100KB.]"
        return content
    except Exception as e:
        return f"Error: {str(e)[:150]}"
