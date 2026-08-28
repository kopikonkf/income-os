"""WebAIAdapter — interface kontrak untuk semua provider web-chat-AI.

Setiap provider (qwen, chatgpt, gemini, mimo, claude, deepseek) mengimplementasi
kontrak ini. Server OpenAI-compatible di src/server.py me-route ke adapter
berdasarkan nama provider.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ChatRequest:
    messages: list[ChatMessage]
    model: Optional[str] = None
    stream: bool = False


@dataclass
class ChatResponse:
    content: str
    model: Optional[str] = None
    usage: dict[str, int] = field(default_factory=dict)


@dataclass
class HealthStatus:
    ok: bool
    detail: str = ""


class RateLimitError(Exception):
    """Provider web-chat-AI sedang kena rate-limit / kuota habis (HTTP 429).

    Server (src/server.py) memakai exception ini untuk fallback chain:
    kalau satu provider 429, request diteruskan ke provider berikutnya.
    """


class WebAIAdapter:
    """Base class — semua adapter wajib override method di bawah."""

    name: str = "base"

    def auth(self) -> dict[str, Any]:
        """Login/refresh token/validasi sesi. Return state auth."""
        raise NotImplementedError

    def chat(self, req: ChatRequest) -> ChatResponse:
        """Kirim pesan, terima jawaban (tanpa streaming dulu di Phase 1)."""
        raise NotImplementedError

    def new_conversation(self) -> None:
        """Reset konteks percakapan (chat id, parent id)."""
        raise NotImplementedError

    def health(self) -> HealthStatus:
        """Cek sesi masih hidup."""
        raise NotImplementedError

    # helper umum
    def _validate(self, req: ChatRequest) -> None:
        if not req.messages:
            raise ValueError("messages kosong")