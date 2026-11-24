from __future__ import annotations

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.application.query_proposal_service import QueryProposalService


def test_query_proposal_has_no_execution_result(tmp_path):
    service = QueryProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(tmp_path / "q.jsonl"))
    ctx = RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))
    proposal = service.propose(
        "buscar conexoes suspeitas",
        {
            "time_window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
            "data_scope": {"index": "netflow"},
            "cost_estimate": {"summary": "estimativa controlada", "estimated_scan_units": 100},
            "query_artifact": {"text": "search suspicious", "language": "kql"},
        },
        ctx,
    )
    assert proposal["requires_human_review"] is True
    assert proposal.get("execution_status") != "executed"
    assert "results" not in proposal
    assert "result_set" not in proposal


def test_incomplete_query_parameters_blocked(tmp_path):
    service = QueryProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(tmp_path / "q.jsonl"))
    ctx = RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))
    proposal = service.propose("objetivo sem parametros", {"query_artifact": {"text": "x"}}, ctx)
    assert proposal["execution_status"] == "blocked"
    assert proposal["data_sufficiency"]["escalation_required"] is True
    assert proposal["policy_decision"]["result"] in {"require_revision", "block_and_escalate"}
