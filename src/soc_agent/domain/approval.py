from __future__ import annotations

from typing import Any

from .common import utc_now_iso


ALLOWED_DECISIONS = {"approved", "rejected"}
ALLOWED_PROPOSAL_TYPES = {"containment", "query_execution"}


def validate_approval_record(record: dict[str, Any]) -> None:
    required = ["approval_id", "proposal_id", "proposal_type", "approver", "decision", "scope", "decided_at"]
    for f in required:
        if f not in record:
            raise ValueError(f"ApprovalRecord missing required field: {f}")
    if record["proposal_type"] not in ALLOWED_PROPOSAL_TYPES:
        raise ValueError(f"Invalid proposal_type: {record['proposal_type']}")
    if record["decision"] not in ALLOWED_DECISIONS:
        raise ValueError(f"Invalid decision: {record['decision']}")
    approver = record.get("approver") or {}
    if not isinstance(approver, dict) or not approver.get("id") or not approver.get("display_name"):
        raise ValueError("ApprovalRecord.approver must include id and display_name")


def is_explicitly_approved(record: dict[str, Any] | None, proposal_id: str, proposal_type: str) -> bool:
    """Explicit linked approval only; absence/invalid => not approved (R2)."""
    if not record:
        return False
    try:
        validate_approval_record(record)
    except Exception:
        return False
    return (
        record.get("proposal_id") == proposal_id
        and record.get("proposal_type") == proposal_type
        and record.get("decision") == "approved"
    )


def approval_status_from_record(record: dict[str, Any] | None, proposal_id: str, proposal_type: str) -> str:
    if not record:
        return "pending"
    try:
        validate_approval_record(record)
    except Exception:
        return "pending"
    if record.get("proposal_id") != proposal_id or record.get("proposal_type") != proposal_type:
        return "pending"
    if record.get("decision") == "approved":
        return "approved"
    if record.get("decision") == "rejected":
        return "rejected"
    return "pending"


def build_approval_record(
    approval_id: str,
    proposal_id: str,
    proposal_type: str,
    decision: str,
    approver_id: str,
    justification: str | None = None,
    scope: dict[str, Any] | None = None,
    decided_at: str | None = None,
) -> dict[str, Any]:
    record = {
        "approval_id": approval_id,
        "proposal_id": proposal_id,
        "proposal_type": proposal_type,
        "approver": {"id": approver_id, "display_name": approver_id},
        "decision": decision,
        "scope": scope or {"target": proposal_id},
        "decided_at": decided_at or utc_now_iso(),
    }
    if justification is not None:
        record["justification"] = justification
    validate_approval_record(record)
    return record
