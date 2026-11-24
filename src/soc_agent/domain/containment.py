from __future__ import annotations

from typing import Any

from .validators import validate_classification, validate_data_sufficiency, validate_hypotheses, validate_trace

REQUIRED_FIELDS = [
    "proposal_id",
    "incident_or_alert_ref",
    "action_category",
    "target",
    "classification",
    "confidence",
    "consulted_sources",
    "rollback_plan",
    "approval_requirement",
    "approval_status",
    "hypotheses",
    "data_sufficiency",
    "policy_decision",
    "trace",
]

ALLOWED_CATEGORIES = {"network", "host", "identity_account", "process", "credential_token"}


def validate_containment_proposal(proposal: dict[str, Any]) -> None:
    for f in REQUIRED_FIELDS:
        if f not in proposal:
            raise ValueError(f"ContainmentProposal missing required field: {f}")
    if proposal.get("action_category") not in ALLOWED_CATEGORIES:
        raise ValueError(f"Invalid action_category: {proposal.get('action_category')}")
    validate_classification(proposal["classification"])
    validate_data_sufficiency(proposal["data_sufficiency"])
    validate_hypotheses(proposal["hypotheses"])
    validate_trace(proposal["trace"])
    if not isinstance(proposal.get("consulted_sources"), list):
        raise ValueError("ContainmentProposal.consulted_sources must be a list")
    if not isinstance(proposal.get("rollback_plan"), dict):
        raise ValueError("ContainmentProposal.rollback_plan must be an object")
    if not isinstance(proposal.get("approval_requirement"), dict):
        raise ValueError("ContainmentProposal.approval_requirement must be an object")
    if proposal.get("approval_requirement", {}).get("execution_permitted") not in (False,):
        # R2: proposal never grants execution permission by itself
        proposal.setdefault("approval_requirement", {})["execution_permitted"] = False


def has_complete_rollback(proposal: dict[str, Any]) -> bool:
    rb = proposal.get("rollback_plan") or {}
    if not isinstance(rb, dict):
        return False
    steps = rb.get("steps")
    summary = str(rb.get("summary") or "").lower()
    responsible = str(rb.get("responsible") or "").lower()
    validation = str(rb.get("validation") or "").lower()
    if not (isinstance(steps, list) and len(steps) > 0):
        return False
    # detect placeholder/blocked rollback inserted for schema compliance
    blocked_markers = ("bloqueado", "ausente", "incompleto", "não definido", "nao definido", "indefinido", "impossível", "impossivel")
    if any(m in summary for m in ("ausente", "incompleto", "não definido", "nao definido", "bloquead")):
        return False
    if any(m in responsible for m in ("indefinido", "a definir")):
        return False
    if any(m in validation for m in ("impossível", "impossivel", "não definido", "nao definido", "a definir")):
        return False
    if any(isinstance(s, str) and s.startswith("BLOQUEADO:") for s in steps):
        return False
    return bool(str(rb.get("summary") or "").strip() and str(rb.get("responsible") or "").strip() and str(rb.get("validation") or "").strip())


def is_target_ambiguous(proposal: dict[str, Any]) -> bool:
    target = proposal.get("target") or {}
    if isinstance(target, dict):
        if target.get("ambiguous") is True:
            return True
        if target.get("unambiguous") is False:
            return True
        if target.get("unambiguous") is True and target.get("identifier") and target.get("type"):
            return False
        ids = target.get("identifier") or target.get("identifiers") or target.get("id") or target.get("asset_id") or target.get("account_id")
        return not bool(ids)
    return True
