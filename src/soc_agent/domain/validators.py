from __future__ import annotations

from typing import Any

ALLOWED_SOURCE_CAPABILITIES = {
    "alert_source",
    "search_backend",
    "enrichment",
    "threat_intel",
    "policy_engine",
    "llm_provider",
    "other",
}
ALLOWED_SOURCE_STATUS = {"ok", "unavailable", "partial", "error", "not_consulted"}


def require_fields(obj: dict[str, Any], fields: list[str], ctx: str) -> None:
    for f in fields:
        if f not in obj:
            raise ValueError(f"Missing required field '{f}' in {ctx}")


def validate_consulted_source(source: dict[str, Any]) -> None:
    require_fields(source, ["capability", "reference", "status", "consulted_at"], "consulted_source")
    if source["capability"] not in ALLOWED_SOURCE_CAPABILITIES:
        raise ValueError(f"Invalid consulted source capability: {source['capability']}")
    if source["status"] not in ALLOWED_SOURCE_STATUS:
        raise ValueError(f"Invalid consulted source status: {source['status']}")


def validate_hypotheses(h: dict[str, Any]) -> None:
    require_fields(h, ["primary", "alternatives"], "hypotheses")
    for key in ("title", "rationale"):
        if key not in h["primary"]:
            raise ValueError(f"Primary hypothesis missing '{key}'")
    alts = h.get("alternatives") or []
    if not isinstance(alts, list) or len(alts) < 1:
        raise ValueError("At least one alternative hypothesis is required")
    for alt in alts:
        for key in ("title", "rationale"):
            if key not in alt:
                raise ValueError(f"Alternative hypothesis missing '{key}'")


def validate_data_sufficiency(ds: dict[str, Any]) -> None:
    require_fields(ds, ["sufficient", "known", "missing", "escalation_required"], "data_sufficiency")
    if not isinstance(ds["known"], list) or not isinstance(ds["missing"], list):
        raise ValueError("data_sufficiency.known and data_sufficiency.missing must be lists")
    if not isinstance(ds["escalation_required"], bool):
        raise ValueError("data_sufficiency.escalation_required must be boolean")


def validate_classification(c: dict[str, Any]) -> None:
    require_fields(c, ["label", "justification"], "classification")


def validate_trace(t: dict[str, Any]) -> None:
    require_fields(t, ["request_id", "created_at"], "trace")
