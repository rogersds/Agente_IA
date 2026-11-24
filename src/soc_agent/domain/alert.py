from __future__ import annotations

from typing import Any

from .validators import require_fields


def validate_alert(alert: dict[str, Any]) -> None:
    require_fields(alert, ["alert_id", "source", "received_at", "content"], "Alert")
    src = alert.get("source") or {}
    if not isinstance(src, dict) or not src.get("source_id"):
        raise ValueError("Alert.source must include source_id")


def normalize_alert(alert: dict[str, Any]) -> dict[str, Any]:
    validate_alert(alert)
    out = dict(alert)
    src = dict(out.get("source") or {})
    src.setdefault("capability", "alert_source")
    out["source"] = src
    return out
