from __future__ import annotations

"""T044/B.4: integração do fluxo de proposta de contenção (alinhamento de nome).

Equivalência explícita: PolicyEngine antes da emissão/finalização, enfileiramento sem execução, transições com
registro explícito aprovado/rejeitado e manutenção de pendente sem registro (conforme serviços/adapters e
testes de contrato/guardrail existentes). Sem caminho de execução destrutiva.
"""

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.approval_service import ApprovalService
from soc_agent.application.containment_proposal_service import ContainmentProposalService
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.common import data_sufficiency, utc_now_iso


def _ctx(tmp_path):
    return RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))


def _params():
    return {
        "action_category": "host",
        "target": {"identifier": "SYNTH-HOST", "type": "host", "unambiguous": True},
        "rollback_plan": {"summary": "S", "preconditions": ["p"], "steps": ["s"], "responsible": "r", "validation": "v", "limitations": []},
        "data_sufficiency": data_sufficiency(True, ["k"], [], False),
    }


def test_t044_containment_flow_enqueue_no_execution_and_explicit_transitions(tmp_path):
    queue = LocalActionProposalQueue(tmp_path / "q.jsonl")
    audit = LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl")
    ctx = RuntimeContext(audit_sink=audit)
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), queue)

    proposal = service.propose("SYNTH-INC", _params(), ctx)
    SchemaValidator().validate("containment-proposal.schema.json", proposal)
    assert proposal.get("policy_decision", {}).get("decision_id")
    assert proposal["approval_requirement"]["execution_permitted"] is False
    stored = queue.get(proposal["proposal_id"]).get("proposal")
    assert stored and "executed" not in stored

    # sem registro explícito permanece não aprovado
    assert stored.get("approval_status") != "approved"

    # aprovação explícita
    app = {"approval_id": "SYNTH-A1", "proposal_id": proposal["proposal_id"], "proposal_type": "containment", "approver": {"id": "SYNTH-H", "display_name": "SYNTH"}, "decision": "approved", "scope": {}, "decided_at": utc_now_iso()}
    ApprovalService(queue).record_decision(app, ctx)
    assert (queue.get(proposal["proposal_id"]).get("proposal") or {}).get("approval_status") == "approved"

    # rejeição explícita em outra proposta
    proposal2 = service.propose("SYNTH-INC2", _params(), ctx)
    rej = {"approval_id": "SYNTH-A2", "proposal_id": proposal2["proposal_id"], "proposal_type": "containment", "approver": {"id": "SYNTH-H", "display_name": "SYNTH"}, "decision": "rejected", "scope": {}, "decided_at": utc_now_iso()}
    ApprovalService(queue).record_decision(rej, ctx)
    assert (queue.get(proposal2["proposal_id"]).get("proposal") or {}).get("approval_status") == "rejected"

    events = audit.read_all()
    assert any(e.get("event_type") == "containment_proposal_created" for e in events)
    assert any(e.get("event_type") == "approval_recorded" for e in events)
