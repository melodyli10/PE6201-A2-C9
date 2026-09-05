"""The ONE function that knows a vendor exists. OpenRouter is OpenAI-chat-completions
compatible, so this is a single HTTP call - stdlib only, no SDK dependency. Everything else
in the codebase (loop.py, the tools) never imports this module directly except through
config.BACKEND, and never sees a vendor-specific shape."""

import json
import os
import urllib.error
import urllib.request

from src import config


def next_turn(messages: list[dict], tools: list[dict] | None = None) -> dict:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in, "
            "or export it, before using BACKEND=live."
        )

    payload = {
        "model": config.MODEL,
        "messages": messages,
        "tools": tools or [],
        "tool_choice": "auto",
    }
    request = urllib.request.Request(
        f"{config.BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"OpenRouter request failed ({exc.code}): {exc.read().decode('utf-8')}") from exc

    if "choices" not in body:
        raise RuntimeError(f"OpenRouter returned no choices - full response: {body}")
    choice = body["choices"][0]["message"]
    message = {
        "role": "assistant",
        "content": choice.get("content"),
        "tool_calls": choice.get("tool_calls") or [],
    }
    usage = body.get("usage", {})
    return {
        "message": message,
        "usage": {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        },
    }
