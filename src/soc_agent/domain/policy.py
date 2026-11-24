from __future__ import annotations

from typing import Any
from uuid import uuid4

from .common import utc_now_iso


ALLOWED_POLICY_RESULTS = {"allow_proposal", "require_revision", "block_and_escalate"}


def build_policy_request(
    request_id: str,
    proposal_kind: str,
    candidate: dict[str, Any],
    context: dict[str, Any],
    requested_at: str | None = None,
) -> dict[str, Any]:
    return {
        "request_id": request_id,
        "proposal_kind": proposal_kind,
        "candidate": candidate,
        "context": context,
        "requested_at": requested_at or utc_now_iso(),
    }


def normalize_policy_decision(raw: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    """Ensure PolicyDecision has required fields per data-model/contracts."""
    result = raw.get("result")
    if result not in ALLOWED_POLICY_RESULTS:
        result = "block_and_escalate"
    reasons = raw.get("reasons") or ["invalid or missing policy reasons; defaulting to block_and_escalate"]
    if not isinstance(reasons, list) or not reasons:
        reasons = [str(reasons)]
    return {
        "decision_id": raw.get("decision_id") or f"pd-{uuid4()}",
        "policy_id": raw.get("policy_id") or "soc_agent.policy.action_proposal",
        "policy_version": raw.get("policy_version") or "unknown",
        "evaluated_at": raw.get("evaluated_at") or utc_now_iso(),
        "input_ref": raw.get("input_ref") or {"request_id": request.get("request_id"), "proposal_kind": request.get("proposal_kind")},
        "result": result,
        "reasons": reasons,
        "required_actions": raw.get("required_actions") or [],
        "obligations": raw.get("obligations") or [],
    }
