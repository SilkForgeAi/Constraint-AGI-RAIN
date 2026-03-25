from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from rain.config import BASE_MODEL_HF, BASE_MODEL_HF_SUBDIR

_mlx_model_cache: dict[str, tuple[Any, Any]] = {}


def _mlx_parse_repo_spec(repo_spec: str) -> tuple[str, str | None]:
    parts = [x for x in (repo_spec or "").strip().split("/") if x]
    if len(parts) < 2:
        raise ValueError(
            f"Invalid MLX BASE_MODEL_HF: {repo_spec!r}. Use org/model or org/model/subfolder."
        )
    return f"{parts[0]}/{parts[1]}", "/".join(parts[2:]) if len(parts) > 2 else None


def _mlx_variant_globs(sub: str) -> list[str]:
    return [
        f"{sub}/*.json",
        f"{sub}/model*.safetensors",
        f"{sub}/model.safetensors.index.json",
        f"{sub}/tokenizer*",
        f"{sub}/*.py",
        f"{sub}/*.txt",
        f"{sub}/*.jinja",
        f"{sub}/tokenizer.model",
        f"{sub}/*.tiktoken",
    ]


def _mlx_infer_subfolder(hf_repo: str) -> str | None:
    try:
        from huggingface_hub import list_repo_files
    except ImportError:
        return None
    try:
        files = list_repo_files(hf_repo)
    except Exception:
        return None
    if "config.json" in files:
        return None
    subs: list[str] = []
    for f in files:
        if f.count("/") == 1 and f.endswith("/config.json"):
            subs.append(f.split("/")[0])
    if not subs:
        return None
    for needle in ("4bit", "3bit", "6bit", "8bit", "bfloat16", "float16"):
        for s in subs:
            if needle in s.lower():
                return s
    return subs[0]


def _mlx_resolve_local_dir(repo_spec: str) -> str:
    from huggingface_hub import snapshot_download

    hf_repo, sub = _mlx_parse_repo_spec(repo_spec)
    if not sub:
        sub = (BASE_MODEL_HF_SUBDIR or "").strip() or None
    if not sub and hf_repo == "mlx-community/DeepSeek-R1-Distill-Qwen-7B-MLX":
        sub = "DeepSeek-R1-Distill-Qwen-7B-4bit"
    if not sub:
        sub = _mlx_infer_subfolder(hf_repo)

    allow_patterns = _mlx_variant_globs(sub) if sub else None
    root = Path(snapshot_download(hf_repo, allow_patterns=allow_patterns))

    if sub:
        local = root / sub
        if not (local / "config.json").exists():
            raise FileNotFoundError(
                f"MLX: expected {local / 'config.json'}. "
                "Set BASE_MODEL_HF=org/repo/subfolder or BASE_MODEL_HF_SUBDIR."
            )
        return str(local)

    if (root / "config.json").exists():
        return str(root)

    variants = sorted(
        [d for d in root.iterdir() if d.is_dir() and (d / "config.json").exists()],
        key=lambda d: d.name.lower(),
    )
    if not variants:
        raise FileNotFoundError(
            f"MLX: no config.json under {root}. "
            "Use org/repo/subfolder or BASE_MODEL_HF_SUBDIR."
        )
    for needle in ("4bit", "3bit", "6bit", "8bit", "bfloat16", "float16"):
        for d in variants:
            if needle in d.name.lower():
                return str(d)
    return str(variants[0])


class MLXBackend:
    provider = "mlx"

    def __init__(self, *, model: str | None = None):
        self.model = model or BASE_MODEL_HF

    def _mlx_messages_to_prompt(self, messages: list[dict[str, str]], tokenizer: Any) -> str:
        msgs: list[dict[str, str]] = []
        for m in messages:
            role = (m.get("role") or "user").lower()
            content = (m.get("content") or "").strip()
            if not content:
                continue
            if role not in ("system", "user", "assistant"):
                continue
            msgs.append({"role": role, "content": content})
        if getattr(tokenizer, "chat_template", None) is not None and msgs:
            try:
                return tokenizer.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
            except Exception:
                pass
        lines: list[str] = []
        for m in msgs:
            lines.append(f"{m['role'].upper()}: {m['content']}")
        lines.append("ASSISTANT:")
        return "\n".join(lines)

    def _mlx_load(self, repo_id: str) -> tuple[Any, Any]:
        global _mlx_model_cache
        if repo_id not in _mlx_model_cache:
            try:
                from mlx_lm import load
            except ImportError as e:
                raise ImportError("Install mlx-lm for RAIN_LLM_PROVIDER=mlx: pip install mlx-lm") from e
            local_dir = _mlx_resolve_local_dir(repo_id)
            print(
                f"[LOG: MLX loading base model] {repo_id} -> {local_dir}",
                file=sys.stderr,
                flush=True,
            )
            _mlx_model_cache[repo_id] = load(local_dir)
        return _mlx_model_cache[repo_id]

    def _mlx_generate_text(
        self,
        model: Any,
        tokenizer: Any,
        prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        try:
            from mlx_lm import generate
            import inspect
        except ImportError as e:
            raise ImportError("Install mlx-lm: pip install mlx-lm") from e
        sig = inspect.signature(generate)
        kwargs: dict[str, Any] = {
            "prompt": prompt,
            "max_tokens": min(max_tokens, 8192),
            "verbose": False,
        }
        if "temp" in sig.parameters:
            kwargs["temp"] = temperature
        elif "temperature" in sig.parameters:
            kwargs["temperature"] = temperature
        out = generate(model, tokenizer, **kwargs)
        if isinstance(out, str):
            return out.strip()
        return str(out).strip()

    def complete(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        repo_id = self.model
        mdl, tok = self._mlx_load(repo_id)
        prompt = self._mlx_messages_to_prompt(messages, tok)
        return self._mlx_generate_text(mdl, tok, prompt, temperature, max_tokens)

    def complete_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Iterator[str]:
        # mlx_lm streaming support varies heavily by version; keep semantics stable (single chunk).
        text = self.complete(messages, temperature, max_tokens)
        if text:
            yield text

