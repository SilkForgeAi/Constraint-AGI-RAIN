"""Runtime config validation (provider deps, required keys).

This intentionally runs at startup so misconfiguration fails fast with a clear
error message rather than failing mid-session.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigIssue:
    level: str  # "error" | "warning"
    message: str


def _has_module(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def validate_provider_config() -> list[ConfigIssue]:
    from rain import config as cfg

    issues: list[ConfigIssue] = []
    provider = (cfg.LLM_PROVIDER or "").strip().lower()

    if provider == "openai":
        if not cfg.OPENAI_API_KEY.strip():
            issues.append(ConfigIssue("error", "OPENAI_API_KEY missing (provider=openai)."))
        if not _has_module("openai"):
            issues.append(ConfigIssue("error", "Python package missing: `openai` (pip install openai)."))

    elif provider == "anthropic":
        if not cfg.ANTHROPIC_API_KEY.strip():
            issues.append(ConfigIssue("error", "ANTHROPIC_API_KEY missing (provider=anthropic)."))
        if not _has_module("anthropic"):
            issues.append(ConfigIssue("error", "Python package missing: `anthropic` (pip install anthropic)."))

    elif provider == "ollama":
        # Ollama uses openai client for compatibility.
        if not _has_module("openai"):
            issues.append(ConfigIssue("error", "Python package missing: `openai` (pip install openai) for Ollama client."))

    elif provider == "mlx":
        if not _has_module("mlx_lm"):
            issues.append(ConfigIssue("error", "Python package missing: `mlx-lm` (pip install mlx-lm)."))
        if not _has_module("huggingface_hub"):
            issues.append(ConfigIssue("error", "Python package missing: `huggingface_hub` (pip install huggingface_hub)."))
        if not (cfg.BASE_MODEL_HF or "").strip():
            issues.append(ConfigIssue("error", "BASE_MODEL_HF missing (provider=mlx)."))

    else:
        issues.append(ConfigIssue("error", f"Unknown RAIN_LLM_PROVIDER/LLM_PROVIDER: {provider!r}"))

    return issues


def validate_or_raise() -> None:
    issues = validate_provider_config()
    errors = [i for i in issues if i.level == "error"]
    if errors:
        msg = "Rain startup configuration errors:\n" + "\n".join(f"- {e.message}" for e in errors)
        raise RuntimeError(msg)

