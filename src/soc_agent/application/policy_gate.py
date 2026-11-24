from __future__ import annotations

from typing import Any

from soc_agent.domain.policy import normalize_policy_decision
from soc_agent.ports.policy_engine import PolicyEngine


def evaluate_before_proposal(engine: PolicyEngine, request: dict[str, Any]) -> dict[str, Any]:
    """Mandatory gate: PolicyEngine must be evaluated before emitting/finalizing proposals."""
    raw = engine.evaluate(request)
    decision = normalize_policy_decision(raw if isinstance(raw, dict) else {}, request)
    # Fail-safe: only explicit allow_proposal/require_revision/block_and_escalate accepted (normalized)
    return decision


def can_emit_proposal(decision: dict[str, Any]) -> bool:
    return decision.get("result") == "allow_proposal"
