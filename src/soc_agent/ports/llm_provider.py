from __future__ import annotations

from typing import Any, Protocol


class LlmProvider(Protocol):
    def generate(self, request: dict[str, Any]) -> dict[str, Any]: ...
