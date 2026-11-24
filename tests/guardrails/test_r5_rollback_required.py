from __future__ import annotations

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.containment_proposal_service import ContainmentProposalService
from soc_agent.application.orchestrator import RuntimeContext


def test_missing_rollback_blocks_or_escalates(tmp_path):
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(tmp_path / "q.jsonl"))
    ctx = RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))
    proposal = service.propose(
        "alert-1",
        {
            "action_category": "network",
            "target": {"identifier": "fw-1", "type": "firewall", "unambiguous": True},
            "rollback_plan": {},  # missing/incomplete
            "data_sufficiency": {"sufficient": True, "known": ["k"], "missing": [], "escalation_required": False},
        },
        ctx,
    )
    assert proposal["approval_status"] == "blocked"
    # policy must not allow actionable emission without rollback when OPA unavailable -> fail-closed; if available, policy blocks/requires revision
    assert proposal["policy_decision"]["result"] in {"require_revision", "block_and_escalate"}
