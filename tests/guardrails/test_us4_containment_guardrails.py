from __future__ import annotations

"""T043/B.4: guardrails R2/R4/R5 para contenção (alinhamento de nome).

Equivalência explícita com `tests/guardrails/test_r2_containment_execution.py`,
`tests/guardrails/test_r5_rollback_required.py` e cobertura em `tests/contract/test_us4_containment_contracts.py`.
Prova bloqueio sem rollback válido, sem alvo inequívoco, com dados insuficientes e sem ApprovalRecord explícito
vinculado (ausência não implica aprovação; sem execução).
Campos citados (data-model/contrato): action_category, target, rollback_plan, approval_requirement,
approval_status, policy_decision; ApprovalRecord.proposal_id/approver/decision/decided_at.
"""

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.approval_service import ApprovalService
from soc_agent.application.containment_proposal_service import ContainmentProposalService
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.domain.common import data_sufficiency, utc_now_iso


def _ctx(tmp_path):
    return RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))


def test_t043_no_rollback_blocks(tmp_path):
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(tmp_path / "q.jsonl"))
    proposal = service.propose("SYNTH-REF", {
        "action_category": "network",
        "target": {"identifier": "SYNTH-T", "type": "fw", "unambiguous": True},
        "rollback_plan": {},
        "data_sufficiency": data_sufficiency(True, ["k"], [], False),
    }, _ctx(tmp_path))
    assert proposal["approval_status"] == "blocked"
    assert proposal["policy_decision"]["result"] in {"require_revision", "block_and_escalate"}


def test_t043_ambiguous_target_blocks(tmp_path):
    import pytest
    from soc_agent.domain.containment import ContainmentAmbiguousTargetBlockedError

    audit_path = tmp_path / "audit.jsonl"
    queue_path = tmp_path / "q.jsonl"
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(queue_path))
    ctx = RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(audit_path))
    # R2/R4 (opção a): alvo ambíguo não gera containment-proposal nem enfileiramento; bloqueio controlado e auditado.
    with pytest.raises(ContainmentAmbiguousTargetBlockedError):
        service.propose(
            "SYNTH-REF",
            {
                "action_category": "host",
                "target": {"ambiguous": True},
                "rollback_plan": {"summary": "S", "steps": ["s"], "responsible": "r", "validation": "v", "limitations": []},
                "data_sufficiency": data_sufficiency(True, ["k"], [], False),
            },
            ctx,
        )
    events = ctx.audit_sink.read_all()
    assert any(e.get("event_type") == "containment_proposal_blocked_ambiguous_target" for e in events)
    assert (not queue_path.exists()) or queue_path.read_text(encoding="utf-8").strip() == ""


def test_t043_insufficient_data_blocks_or_escalates(tmp_path):
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(tmp_path / "q.jsonl"))
    proposal = service.propose("SYNTH-REF", {
        "action_category": "host",
        "target": {"identifier": "SYNTH-T", "type": "host", "unambiguous": True},
        "rollback_plan": {"summary": "S", "steps": ["s"], "responsible": "r", "validation": "v", "limitations": []},
        "data_sufficiency": data_sufficiency(False, ["k"], ["m"], True, "SYNTH"),
    }, _ctx(tmp_path))
    assert proposal["data_sufficiency"]["escalation_required"] is True
    assert proposal["approval_status"] == "blocked"


def test_t043_without_explicit_approval_record_never_approved_or_executed(tmp_path):
    queue = LocalActionProposalQueue(tmp_path / "q.jsonl")
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), queue)
    ctx = _ctx(tmp_path)
    proposal = service.propose("SYNTH-REF", {
        "action_category": "host",
        "target": {"identifier": "SYNTH-T", "type": "host", "unambiguous": True},
        "rollback_plan": {"summary": "S", "steps": ["s"], "responsible": "r", "validation": "v", "limitations": []},
        "data_sufficiency": data_sufficiency(True, ["k"], [], False),
    }, ctx, approval_record=None)
    assert proposal["approval_status"] != "approved"
    assert proposal["approval_requirement"]["execution_permitted"] is False
    assert "executed" not in proposal
    stored = queue.get(proposal["proposal_id"]).get("proposal") or {}
    assert stored.get("approval_status") != "approved"

    # progressão/aprovação só com registro explícito vinculado
    record = {"approval_id": "SYNTH-APR", "proposal_id": proposal["proposal_id"], "proposal_type": "containment", "approver": {"id": "SYNTH-H", "display_name": "SYNTH"}, "decision": "approved", "scope": {}, "decided_at": utc_now_iso()}
    res = ApprovalService(queue).record_decision(record, ctx)
    assert res["status"] == "recorded"
    assert (queue.get(proposal["proposal_id"]).get("proposal") or {}).get("approval_status") == "approved"
