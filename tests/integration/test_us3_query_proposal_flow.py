from __future__ import annotations

"""T038/B.4: integração da proposta de consulta (alinhamento de nome).

Equivalência explícita: valida PolicyEngine antes de enfileirar e registra auditoria, conforme
`QueryProposalService.propose` e coberturas em guardrails/contratos B.2; sem execução automática (R7/R2).
"""

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.application.query_proposal_service import QueryProposalService
from soc_agent.contracts_runtime.validator import SchemaValidator


def test_t038_query_proposal_flow_policy_gate_enqueue_and_audit(tmp_path):
    queue = LocalActionProposalQueue(tmp_path / "q.jsonl")
    audit = LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl")
    ctx = RuntimeContext(audit_sink=audit)
    service = QueryProposalService(OpaPolicyEngineAdapter(), queue)

    proposal = service.propose(
        objective="SYNTH-INVESTIGACAO",
        params={
            "time_window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
            "data_scope": {"index": "SYNTH-IDX"},
            "cost_estimate": {"summary": "SYNTH", "estimated_scan_units": 5},
            "query_artifact": {"text": "SYNTH", "language": "kql", "version": "v1"},
        },
        ctx=ctx,
        request_id="SYNTH-REQ-QFLOW",
    )

    SchemaValidator().validate("query-proposal.schema.json", proposal)
    assert proposal.get("policy_decision", {}).get("decision_id")
    assert proposal.get("trace", {}).get("policy_version") is not None or proposal.get("policy_decision", {}).get("policy_version")
    stored = queue.get(proposal["query_proposal_id"]).get("proposal")
    assert stored and stored.get("query_proposal_id") == proposal["query_proposal_id"]
    assert stored.get("execution_status") != "executed"
    events = audit.read_all()
    assert any(e.get("event_type") == "query_proposal_created" for e in events)
    # policy avaliada antes da emissão/finalização (decision registrada na proposta enfileirada)
    assert stored.get("policy_decision", {}).get("result") in {"allow_proposal", "require_revision", "block_and_escalate"}
