from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any


class LocalAppendOnlyAuditSink:
    """Pilot append-only sink backed by JSONL; no in-place edits/removal by agent."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._events: list[dict[str, Any]] = []
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        self._events.append(json.loads(line))
                    except Exception:
                        pass

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._events.append(event)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
                f.flush()
        return {"status": "appended", "audit_id": event.get("audit_id")}

    def query(self, request: dict[str, Any] | None = None) -> dict[str, Any]:
        req = request or {}
        etype = req.get("event_type")
        events = list(self._events)
        if etype:
            events = [e for e in events if e.get("event_type") == etype]
        return {"events": events, "count": len(events)}

    def read_all(self) -> list[dict[str, Any]]:
        return list(self._events)

    @property
    def events(self) -> list[dict[str, Any]]:
        return list(self._events)
