from __future__ import annotations

import json

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.containment_proposal_service import ContainmentProposalService
from soc_agent.application.orchestrator import RuntimeContext


def test_containment_proposal_never_executes_and_blocks_without_explicit_approval(tmp_path):
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(tmp_path / "q.jsonl"))
    ctx = RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))
    proposal = service.propose(
        "alert-1",
        {
            "action_category": "host",
            "target": {"identifier": "host-1", "type": "host", "unambiguous": True},
            "rollback_plan": {
                "summary": "Reverter isolamento",
                "preconditions": ["ok"],
                "steps": ["revert"],
                "responsible": "soc",
                "validation": "check",
                "limitations": ["none"],
            },
            "data_sufficiency": {"sufficient": True, "known": ["k"], "missing": [], "escalation_required": False},
        },
        ctx,
        approval_record=None,
    )
    # R2: no execution performed by system; proposal only
    assert "executed" not in proposal
    assert proposal["approval_requirement"]["execution_permitted"] is False
    # absence of explicit approval must not mean approved
    assert proposal["approval_status"] in {"pending", "blocked", "escalated", "awaiting_approval"}
    assert proposal["approval_status"] != "approved"
    # queue contains proposal artifact only
    q = json.loads((tmp_path / "q.jsonl").read_text(encoding="utf-8").strip())
    assert q.get("proposal_id") == proposal["proposal_id"]
    assert "executed" not in q
