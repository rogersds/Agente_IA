from __future__ import annotations

from typing import Any, Protocol


class ThreatIntelStore(Protocol):
    def lookup(self, request: dict[str, Any]) -> dict[str, Any]: ...
