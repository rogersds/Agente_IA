from __future__ import annotations

from typing import Any, Protocol


class EnrichmentProvider(Protocol):
    def enrich(self, request: dict[str, Any]) -> dict[str, Any]: ...
