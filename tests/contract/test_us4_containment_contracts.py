from __future__ import annotations

"""T042/B.2: contratos ContainmentProposal, ApprovalRecord e ActionProposalQueue (R2/R4/R5).

Equivalências explícitas (B.4): ausência de execução e bloqueio por rollback/alvo/ausência de aprovação também
cobertos em `tests/guardrails/test_r2_containment_execution.py`, `tests/guardrails/test_r5_rollback_required.py`
e fluxos de integração quando presentes.
"""

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.approval_service import ApprovalService
from soc_agent.application.containment_proposal_service import ContainmentProposalService
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.common import classification, consulted_source, data_sufficiency, hypotheses, hypothesis, make_trace, utc_now_iso


def _ctx(tmp_path):
    return RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))


def _valid_containment_params():
    return {
        "action_category": "host",
        "target": {"identifier": "SYNTH-HOST-01", "type": "host", "unambiguous": True},
        "rollback_plan": {
            "summary": "Reverter isolamento do ativo",
            "preconditions": ["janela aprovada", "comando de reversão validado"],
            "steps": ["remover bloqueio aplicado", "validar conectividade"],
            "responsible": "SYNTH-RESP-TEAM",
            "validation": "confirmar retorno de telemetria e acesso autorizado",
            "limitations": ["pode exigir janela de manutenção"],
        },
        "confidence": "low",
        "consulted_sources": [consulted_source("other", {"ref": "SYNTH-ALERT-1"}, "ok", utc_now_iso())],
        "data_sufficiency": data_sufficiency(True, known=["alvo_identificado", "evidencia_minima"], missing=[], escalation_required=False),
    }


def test_containment_and_queue_contracts_with_valid_proposal(tmp_path):
    """T042: ContainmentProposal válido + ActionProposalQueue request/response."""
    queue = LocalActionProposalQueue(tmp_path / "q.jsonl")
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), queue)
    proposal = service.propose("SYNTH-INC-01", _valid_containment_params(), _ctx(tmp_path), request_id="SYNTH-REQ-CP-01")

    v = SchemaValidator()
    v.validate("containment-proposal.schema.json", proposal)
    # R2: alvo exato, rollback declarado, requisito de aprovação humana, sem permissão de execução
    assert proposal["target"]["identifier"] == "SYNTH-HOST-01" and proposal["target"]["unambiguous"] is True
    assert proposal["rollback_plan"]["summary"]
    assert isinstance(proposal["rollback_plan"]["steps"], list) and len(proposal["rollback_plan"]["steps"]) >= 1
    assert proposal["rollback_plan"]["validation"]
    assert proposal["approval_requirement"]["requires_human_approval"] is True
    assert proposal["approval_requirement"]["identified_approver_required"] is True
    assert proposal["approval_requirement"]["execution_permitted"] is False
    assert proposal.get("executed") is None
    assert proposal["trace"]["request_id"] == "SYNTH-REQ-CP-01"

    enqueue_req = {"operation": "enqueue", "requested_at": utc_now_iso(), "proposal": proposal}
    v.validate("action-proposal-queue.request.schema.json", enqueue_req)
    enq_resp = queue.enqueue(proposal)
    v.validate("action-proposal-queue.response.schema.json", enq_resp)

    get_req = {"operation": "get", "requested_at": utc_now_iso(), "proposal_id": proposal["proposal_id"]}
    v.validate("action-proposal-queue.request.schema.json", get_req)
    get_resp = queue.get(proposal["proposal_id"])
    v.validate("action-proposal-queue.response.schema.json", get_resp)


def test_approval_record_contract_and_queue_update(tmp_path):
    """T042: ApprovalRecord e atualização de fila via registro explícito vinculado (sem execução)."""
    queue = LocalActionProposalQueue(tmp_path / "q.jsonl")
    v = SchemaValidator()
    ctx = _ctx(tmp_path)
    cp_service = ContainmentProposalService(OpaPolicyEngineAdapter(), queue)
    proposal = cp_service.propose("SYNTH-INC-02", _valid_containment_params(), ctx)

    record = {
        "approval_id": "SYNTH-APR-01",
        "proposal_id": proposal["proposal_id"],
        "proposal_type": "containment",
        "approver": {"id": "SYNTH-APPROVER-01", "display_name": "SYNTH HUMAN"},
        "decision": "approved",
        "scope": {"action": "containment_host", "target": proposal["target"]["identifier"]},
        "decided_at": utc_now_iso(),
        "notes": "SYNTH-APROVACAO-EXPLICITA",
    }
    v.validate("approval-record.schema.json", record)

    status_req = {"operation": "update_status", "requested_at": utc_now_iso(), "status_update": {"proposal_id": proposal["proposal_id"], "new_status": "approved", "approval_record": record}}
    v.validate("action-proposal-queue.request.schema.json", status_req)

    result = ApprovalService(queue).record_decision(record, ctx)
    assert result["status"] == "recorded"
    assert result["proposal_id"] == proposal["proposal_id"]
    # progresso depende de registro explícito; sem execução automática
    stored = queue.get(proposal["proposal_id"]).get("proposal") or {}
    assert stored.get("approval_status") == "approved" or stored.get("approval_record", {}).get("proposal_id") == proposal["proposal_id"]
    v.validate("action-proposal-queue.response.schema.json", queue.get(proposal["proposal_id"]))


def test_containment_proposal_without_explicit_approval_record_is_not_approved_and_not_executed(tmp_path):
    """T042/B.2/R2: sem ApprovalRecord explícito vinculado não há aprovação nem execução; proposta permanece bloqueada/pendente conforme política."""
    queue = LocalActionProposalQueue(tmp_path / "q.jsonl")
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), queue)
    proposal = service.propose("SYNTH-INC-03", _valid_containment_params(), _ctx(tmp_path), approval_record=None)

    SchemaValidator().validate("containment-proposal.schema.json", proposal)
    assert proposal["approval_status"] != "approved"
    assert proposal["approval_requirement"]["execution_permitted"] is False
    assert "executed" not in proposal and "execution_result" not in proposal
    # sem registro explícito não pode ser tratado como aprovado
    stored = queue.get(proposal["proposal_id"]).get("proposal") or {}
    assert stored.get("approval_status") != "approved"
