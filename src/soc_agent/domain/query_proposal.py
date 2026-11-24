from __future__ import annotations

from typing import Any

from .validators import validate_classification, validate_data_sufficiency, validate_hypotheses, validate_trace

REQUIRED_FIELDS = [
    "query_proposal_id",
    "objective",
    "classification",
    "confidence",
    "consulted_sources",
    "query_artifact",
    "execution_status",
    "requires_human_review",
    "hypotheses",
    "data_sufficiency",
    "policy_decision",
    "trace",
]


def validate_query_proposal(proposal: dict[str, Any]) -> None:
    for f in REQUIRED_FIELDS:
        if f not in proposal:
            raise ValueError(f"QueryProposal missing required field: {f}")
    validate_classification(proposal["classification"])
    validate_data_sufficiency(proposal["data_sufficiency"])
    validate_hypotheses(proposal["hypotheses"])
    validate_trace(proposal["trace"])
    if proposal.get("requires_human_review") is not True:
        # R7: production execution requires human review
        proposal["requires_human_review"] = True
    if not isinstance(proposal.get("consulted_sources"), list):
        raise ValueError("QueryProposal.consulted_sources must be a list")
    if not isinstance(proposal.get("policy_decision"), dict):
        raise ValueError("QueryProposal.policy_decision must be an object")


def query_parameters_complete(proposal: dict[str, Any]) -> bool:
    tw = proposal.get("time_window")
    ds = proposal.get("data_scope")
    ce = proposal.get("cost_estimate")
    return bool(tw and ds and ce)
