from __future__ import annotations
import json
import time
import uuid

def sse_format_openai(
    delta_content: str | None = None,
    role: str | None = None,
    finish: str | None = None,
    model: str = "gemini-2.5-flash"
) -> str:
    delta = {}
    if role:
        delta["role"] = role
    if delta_content is not None:
        delta["content"] = delta_content

    data = {
        "id": f"chatcmpl-{uuid.uuid4().hex}",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish
            }
        ]
    }
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

def sse_done() -> str:
    return "data: [DONE]\n\n"