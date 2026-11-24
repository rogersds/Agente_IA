from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def make_trace(
    request_id: str,
    created_at: str | None = None,
    model_version: str | None = None,
    prompt_version: str | None = None,
    policy_version: str | None = None,
    agent_version: str | None = "0.1.0",
    initiator: Any = None,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "created_at": created_at or utc_now_iso(),
        "model_version": model_version,
        "prompt_version": prompt_version,
        "policy_version": policy_version,
        "agent_version": agent_version,
        "initiator": initiator,
    }


def consulted_source(
    capability: str,
    reference: Any,
    status: str,
    consulted_at: str | None = None,
    source_id: str | None = None,
    details: Any = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "capability": capability,
        "reference": reference,
        "status": status,
        "consulted_at": consulted_at or utc_now_iso(),
        "details": details,
    }
    if source_id:
        out["source_id"] = source_id
    return out


def classification(label: str, justification: str, severity: str | None = None) -> dict[str, Any]:
    out = {"label": label, "justification": justification}
    if severity is not None:
        out["severity"] = severity
    return out


def data_sufficiency(
    sufficient: bool,
    known: list[str] | None = None,
    missing: list[str] | None = None,
    escalation_required: bool = False,
    escalation_reason: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "sufficient": sufficient,
        "known": known or [],
        "missing": missing or [],
        "escalation_required": escalation_required,
    }
    if escalation_reason:
        out["escalation_reason"] = escalation_reason
    return out


def hypothesis(title: str, rationale: str, is_false_positive: bool = False) -> dict[str, Any]:
    return {"title": title, "rationale": rationale, "is_false_positive": is_false_positive}


def hypotheses(primary: dict[str, Any], alternatives: list[dict[str, Any]]) -> dict[str, Any]:
    if not alternatives:
        raise ValueError("At least one alternative hypothesis is required")
    return {"primary": primary, "alternatives": alternatives}
