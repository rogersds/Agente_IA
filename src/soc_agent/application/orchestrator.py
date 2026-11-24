from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from soc_agent.domain.audit import build_audit_event
from soc_agent.domain.common import utc_now_iso
from soc_agent.ports.audit_sink import AuditSink


@dataclass
class RuntimeContext:
    audit_sink: AuditSink
    agent_version: str = "0.1.0"
    prompt_version: str = "prompt-v1"


def emit_audit(
    ctx: RuntimeContext,
    event_type: str,
    input_summary: Any,
    reasoning_summary: str,
    outcome: Any,
    consulted_sources: list[dict[str, Any]] | None = None,
    confidence: Any = None,
    model_version: str | None = None,
    prompt_version: str | None = None,
    policy_version: str | None = None,
    correlation_refs: list[str] | None = None,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = build_audit_event(
        event_type=event_type,
        input_summary=input_summary,
        reasoning_summary=reasoning_summary,
        outcome=outcome,
        consulted_sources=consulted_sources,
        confidence=confidence,
        model_version=model_version,
        prompt_version=prompt_version or ctx.prompt_version,
        policy_version=policy_version,
        correlation_refs=correlation_refs,
        trace=trace,
    )
    ctx.audit_sink.append(event)
    return event


def unavailable_source(capability: str, reference: Any, reason: str, source_id: str | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "capability": capability,
        "reference": reference,
        "status": "unavailable",
        "consulted_at": utc_now_iso(),
        "details": reason,
    }
    if source_id is not None:
        out["source_id"] = str(source_id)
    return out
