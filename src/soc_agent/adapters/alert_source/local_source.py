from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class LocalAlertSourceAdapter:
    """Read-only local alert source for pilot (files/fixtures)."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path("tests/fixtures/alerts")

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        p = self.base_dir / f"{alert_id}.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
        # also search inside files for matching alert_id
        if self.base_dir.exists():
            for f in self.base_dir.glob("*.json"):
                try:
                    data = json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    continue
                if str(data.get("alert_id")) == alert_id:
                    return data
        return None

    def list_alerts(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        if not self.base_dir.exists():
            return items
        for f in sorted(self.base_dir.glob("*.json")):
            try:
                items.append(json.loads(f.read_text(encoding="utf-8")))
            except Exception:
                continue
        return items
