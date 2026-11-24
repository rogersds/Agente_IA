from __future__ import annotations

"""T036/B.2: contratos SearchBackend e QueryProposal (R7, sem execução direta).

Coberturas complementares (equivalência explícita, B.4): ausência de execução direta e bloqueio por parâmetros
incompletos também exercitados em `tests/guardrails/test_r7_query_proposal_only.py`; avaliação PolicyEngine antes
de enfileirar em `tests/integration/test_us3_query_proposal_flow.py` (se presente) e no fluxo do serviço.
"""

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.application.query_proposal_service import QueryProposalService
from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.common import utc_now_iso


def _ctx(tmp_path):
    return RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))


def test_search_backend_request_response_contracts():
    """T036: schemas SearchBackend request/response."""
    validator = SchemaValidator()
    req = {
        "request_id": "SYNTH-SB-REQ-01",
        "objective": "investigar atividade suspeita",
        "requested_at": utc_now_iso(),
        "query": {"text": "SYNTH-QUERY-TEXT", "language": "kql"},
        "time_window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
        "data_scope": {"index": "SYNTH-IDX", "sources": ["SYNTH-SRC-A"]},
        "limits": {"max_rows": 100},
        "dry_run": True,
    }
    validator.validate("search-backend.request.schema.json", req)

    resp = {
        "request_id": "SYNTH-SB-REQ-01",
        "status": "ok",
        "consulted_at": utc_now_iso(),
        "results": [],
        "summary": "SYNTH-SEM-EXECUCAO-REAL",
        "estimated_cost": {"summary": "estimativa controlada", "estimated_scan_units": 10},
    }
    validator.validate("search-backend.response.schema.json", resp)


def test_query_proposal_contract_complete_params_no_direct_execution(tmp_path):
    """T036/B.2: query com janela/escopo/custo explícitos, parâmetros nomeados (sentinelas), artefato versionável, sem execução (R7)."""
    service = QueryProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(tmp_path / "q.jsonl"))
    proposal = service.propose(
        objective="buscar conexoes suspeitas",
        params={
            "time_window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
            "data_scope": {"index": "SYNTH-IDX-NET", "sources": ["SYNTH-SRC-NETFLOW"]},
            "cost_estimate": {"summary": "estimativa controlada", "estimated_scan_units": 100},
            "query_artifact": {"language": "kql", "text": "SYNTH_QUERY_PLACEHOLDER", "version": "v1"},
            "parameter_justification": "Janela, escopo e custo definidos para revisão humana (R7).",
        },
        ctx=_ctx(tmp_path),
        request_id="SYNTH-REQ-QP-01",
    )

    SchemaValidator().validate("query-proposal.schema.json", proposal)
    assert proposal["time_window"]["start"] and proposal["time_window"]["end"]
    assert proposal["data_scope"] is not None
    assert proposal["cost_estimate"] is not None
    assert isinstance(proposal.get("query_artifact"), (dict, str))
    # R7/R2: sem execução direta em produção
    assert proposal["requires_human_review"] is True
    assert proposal.get("execution_status") != "executed"
    assert "results" not in proposal and "result_set" not in proposal and "executed_at" not in proposal
    assert proposal.get("trace", {}).get("request_id") == "SYNTH-REQ-QP-01"


def test_query_proposal_contract_incomplete_params_requires_review_or_block(tmp_path):
    """T036/B.2: parâmetros ausentes => justificação, revisão humana e sem execução."""
    service = QueryProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(tmp_path / "q.jsonl"))
    proposal = service.propose(
        objective="objetivo sem parametros completos",
        params={"query_artifact": {"text": "SYNTH_QUERY"}},
        ctx=_ctx(tmp_path),
        request_id="SYNTH-REQ-QP-02",
    )
    SchemaValidator().validate("query-proposal.schema.json", proposal)
    assert proposal["parameter_justification"]
    assert proposal["requires_human_review"] is True
    assert proposal.get("execution_status") in {"blocked", "pending_review"}
    assert proposal.get("execution_status") != "executed"
    assert proposal["policy_decision"]["result"] in {"require_revision", "block_and_escalate"}
