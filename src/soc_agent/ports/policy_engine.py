from __future__ import annotations

from typing import Any, Protocol


class PolicyEngine(Protocol):
    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]: ...
