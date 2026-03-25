"""Audit log — action history for governance. Tamper-evident via hash chain."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


def _hash_payload(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditLog:
    """Logs actions for oversight and explainability. Hash chain makes tampering detectable."""

    def __init__(self, log_path: Path):
        self._path = log_path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self._path.open("a", encoding="utf-8")
        self._prev_hash = self._read_tail_hash()

    def _read_tail_hash(self) -> str:
        """Get hash from last line, or empty if no entries."""
        last = ""
        try:
            with self._path.open("r", encoding="utf-8") as f:
                for line in f:
                    last = line
                if last.strip():
                    entry = json.loads(last.strip())
                    return entry.get("hash", "")
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            pass
        return ""

    def log(self, action: str, details: dict | None = None, outcome: str = "ok") -> None:
        """Append an audit entry with hash chain."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {},
            "outcome": outcome,
            "prev_hash": self._prev_hash,
        }
        payload = json.dumps(entry, sort_keys=True)
        h = _hash_payload(payload)
        entry["hash"] = h
        self._prev_hash = h
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def verify(self) -> tuple[bool, list[str]]:
        """Verify hash chain. Returns (ok, list of error messages). Legacy entries without hash are skipped."""
        errors: list[str] = []
        prev = ""
        try:
            with self._path.open("r", encoding="utf-8") as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError as e:
                        errors.append(f"Line {i}: invalid JSON: {e}")
                        continue
                    stored_hash = entry.pop("hash", None)
                    if stored_hash is None:
                        prev = ""  # Legacy entry, can't verify; reset chain
                        continue
                    entry["prev_hash"] = prev
                    payload = json.dumps(entry, sort_keys=True)
                    expected = _hash_payload(payload)
                    if stored_hash != expected:
                        errors.append(f"Line {i}: hash mismatch (chain broken)")
                    prev = stored_hash
        except FileNotFoundError:
            return True, []  # Empty file is valid
        return len(errors) == 0, errors
