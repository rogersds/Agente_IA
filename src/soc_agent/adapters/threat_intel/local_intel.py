from __future__ import annotations

from typing import Any


class LocalThreatIntelAdapter:
    def __init__(self, indicators: dict[str, Any] | None = None):
        self.indicators = indicators or {}

    def lookup(self, request: dict[str, Any]) -> dict[str, Any]:
        indicator = str((request or {}).get("indicator") or "")
        return {"indicator": request.get("indicator"), "status": "ok", "matches": self.indicators.get(indicator, [])}
