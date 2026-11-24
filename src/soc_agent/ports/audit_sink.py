from __future__ import annotations

from typing import Any, Protocol


class AuditSink(Protocol):
    def append(self, event: dict[str, Any]) -> dict[str, Any]: ...

    def query(self, request: dict[str, Any] | None = None) -> dict[str, Any]: ...
