"""Registry provider -> instance adapter."""

from __future__ import annotations

from typing import Optional

from .adapter import WebAIAdapter


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, WebAIAdapter] = {}

    def register(self, adapter: WebAIAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> Optional[WebAIAdapter]:
        return self._adapters.get(name)

    def names(self) -> list[str]:
        return sorted(self._adapters.keys())

    def default(self) -> Optional[WebAIAdapter]:
        for prefer in ("qwen", "chatgpt", "gemini", "mimo", "claude", "deepseek"):
            if prefer in self._adapters:
                return self._adapters[prefer]
        return next(iter(self._adapters.values()), None)


registry = AdapterRegistry()