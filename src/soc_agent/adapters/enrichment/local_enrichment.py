from __future__ import annotations

from typing import Any


class LocalEnrichmentAdapter:
    def __init__(self, data: dict[str, Any] | None = None):
        self.data = data or {}

    def enrich(self, request: dict[str, Any]) -> dict[str, Any]:
        subject = str((request or {}).get("subject") or "")
        return {"subject": request.get("subject"), "status": "ok", "data": self.data.get(subject, {})}
