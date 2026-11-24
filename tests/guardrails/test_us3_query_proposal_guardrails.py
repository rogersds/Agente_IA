from __future__ import annotations

"""T037/B.4: guardrails R7/R2 para propostas de consulta (alinhamento de nome).

Equivalência explícita: cobertura consolidada com `tests/guardrails/test_r7_query_proposal_only.py`
(sem execução automática, requires_human_review, parâmetros ausentes => bloqueio/revisão conforme política).
Campos citados (data-model/contrato): time_window, data_scope, cost_estimate, requires_human_review,
execution_status, policy_decision. Nenhuma execução de query em produção.
"""

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.application.query_proposal_service import QueryProposalService


def _ctx(tmp_path):
    return RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))


def test_t037_query_missing_params_blocks_or_requires_review_and_never_executes(tmp_path):
    service = QueryProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(tmp_path / "q.jsonl"))
    proposal = service.propose("SYNTH-OBJ", {"query_artifact": {"text": "SYNTH"}}, _ctx(tmp_path))
    assert proposal["requires_human_review"] is True
    assert proposal.get("execution_status") in {"blocked", "pending_review"}
    assert proposal.get("execution_status") != "executed"
    assert "results" not in proposal and "result_set" not in proposal
    assert proposal["policy_decision"]["result"] in {"require_revision", "block_and_escalate"}


def test_t037_query_complete_params_still_human_review_only(tmp_path):
    service = QueryProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(tmp_path / "q.jsonl"))
    proposal = service.propose(
        "SYNTH-OBJ",
        {
            "time_window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
            "data_scope": {"index": "SYNTH-IDX"},
            "cost_estimate": {"summary": "SYNTH", "estimated_scan_units": 1},
            "query_artifact": {"text": "SYNTH", "language": "kql"},
        },
        _ctx(tmp_path),
    )
    assert proposal["requires_human_review"] is True
    assert proposal.get("execution_status") != "executed"
    assert "executed_at" not in proposal
