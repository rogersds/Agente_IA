from __future__ import annotations

from typing import Any


class LocalSearchBackendAdapter:
    def __init__(self, events: list[dict[str, Any]] | None = None):
        self.events = events or []

    def search(self, query_request: dict[str, Any]) -> dict[str, Any]:
        # Read-only query execution for pilot evidence collection (not a proposal artifact path)
        return {
            "request_id": query_request.get("request_id", "local-search"),
            "status": "ok",
            "executed": True,
            "results": list(self.events),
            "note": "Local pilot read-only search over provided dataset.",
        }
