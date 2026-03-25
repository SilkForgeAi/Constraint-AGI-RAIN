"""Embodied perception — vision: describe image from path or base64.

Uses LLM vision when provider supports it (OpenAI, Anthropic). Otherwise returns placeholder.
"""

from __future__ import annotations

import base64
import mimetypes
from pathlib import Path


def describe_image(
    image_path: str = "",
    image_base64: str = "",
    mime_type: str = "",
    engine: object = None,
    max_tokens: int = 400,
) -> str:
    """
    Describe the content of an image. Provide either image_path (file path) or image_base64.
    When engine supports vision (OpenAI/Anthropic with vision model), returns LLM description.
    Otherwise returns a fallback message.
    """
    data_url = ""
    if image_base64:
        mime = mime_type or "image/png"
        data_url = f"data:{mime};base64,{image_base64}"
    elif image_path:
        path = Path(image_path).expanduser().resolve()
        if not path.exists():
            return f"Error: Image file not found: {path}"
        try:
            with open(path, "rb") as f:
                b64 = base64.standard_b64encode(f.read()).decode("ascii")
            mime = mime_type or (mimetypes.guess_type(str(path))[0] or "image/png")
            data_url = f"data:{mime};base64,{b64}"
        except Exception as e:
            return f"Error reading image: {e}"
    if not data_url:
        return "Error: Provide image_path or image_base64."

    if engine is None:
        try:
            from rain.core.engine import CoreEngine
            engine = CoreEngine()
        except Exception:
            return "Vision: engine not available. Install and set OPENAI_API_KEY or ANTHROPIC_API_KEY for vision models."

    # Try vision-capable completion (OpenAI/Anthropic accept content with image_url or type image_url)
    try:
        provider = getattr(engine, "provider", "")
        if provider == "openai":
            return _openai_vision(engine, data_url, max_tokens)
        if provider == "anthropic":
            return _anthropic_vision(engine, data_url, max_tokens)
    except Exception as e:
        return f"Vision description failed: {e}"

    return "Vision: current provider does not support image input. Use OpenAI or Anthropic with a vision-capable model."


def _openai_vision(engine: object, data_url: str, max_tokens: int) -> str:
    try:
        from openai import OpenAI
        from rain.config import OPENAI_API_KEY
        client = OpenAI(api_key=OPENAI_API_KEY, timeout=60.0)
        model = getattr(engine, "model", "gpt-4o-mini")
        msg = [
            {"role": "user", "content": [
                {"type": "text", "text": "Describe this image concisely: layout, objects, text if any, and any notable details."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ]},
        ]
        r = client.chat.completions.create(model=model, messages=msg, max_tokens=max_tokens)
        if r.choices and r.choices[0].message.content:
            return r.choices[0].message.content
    except Exception as e:
        return f"OpenAI vision error: {e}"
    return "No description returned."


def _anthropic_vision(engine: object, data_url: str, max_tokens: int) -> str:
    try:
        import anthropic
        from rain.config import ANTHROPIC_API_KEY
        model = getattr(engine, "model", "claude-sonnet-4-20250514")
        # Anthropic expects source with type base64 and media_type
        import re
        match = re.match(r"data:([^;]+);base64,(.+)", data_url)
        if not match:
            return "Invalid data URL."
        media_type, b64 = match.group(1), match.group(2)
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=60.0)
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image concisely: layout, objects, text if any, and notable details."},
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}},
                ],
            }],
        )
        if msg.content and msg.content[0].text:
            return msg.content[0].text
    except Exception as e:
        return f"Anthropic vision error: {e}"
    return "No description returned."
