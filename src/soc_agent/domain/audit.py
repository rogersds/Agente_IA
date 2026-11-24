from __future__ import annotations

from typing import Any
from uuid import uuid4

from .common import utc_now_iso


def build_audit_event(
    event_type: str,
    input_summary: Any,
    reasoning_summary: str,
    outcome: Any,
    occurred_at: str | None = None,
    consulted_sources: list[dict[str, Any]] | None = None,
    confidence: Any = None,
    model_version: str | None = None,
    prompt_version: str | None = None,
    policy_version: str | None = None,
    correlation_refs: list[str] | None = None,
    audit_id: str | None = None,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "audit_id": audit_id or f"audit-{uuid4()}",
        "event_type": event_type,
        "occurred_at": occurred_at or utc_now_iso(),
        "input_summary": input_summary,
        "reasoning_summary": reasoning_summary,
        "outcome": outcome,
    }
    if consulted_sources is not None:
        event["consulted_sources"] = consulted_sources
    if confidence is not None:
        event["confidence"] = confidence
    # R6: versões e trace para rastreabilidade (quando disponíveis)
    if trace and trace.get("model_version") is not None and model_version is None:
        model_version = trace.get("model_version")
    if trace and trace.get("prompt_version") is not None and prompt_version is None:
        prompt_version = trace.get("prompt_version")
    if trace and trace.get("policy_version") is not None and policy_version is None:
        policy_version = trace.get("policy_version")
    if model_version is not None:
        event["model_version"] = model_version
    if prompt_version is not None:
        event["prompt_version"] = prompt_version
    if policy_version is not None:
        event["policy_version"] = policy_version
    if correlation_refs is not None:
        event["correlation_refs"] = correlation_refs
    if trace is not None:
        event["trace"] = trace
    return event
