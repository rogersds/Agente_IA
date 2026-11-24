from __future__ import annotations

from typing import Any, Protocol


class AlertSource(Protocol):
    def fetch_alerts(self, request: dict[str, Any]) -> dict[str, Any]: ...

    def get_alert(self, request: dict[str, Any]) -> dict[str, Any]: ...
