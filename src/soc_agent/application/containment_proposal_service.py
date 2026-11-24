from __future__ import annotations

from typing import Any
from uuid import uuid4

from soc_agent.application.orchestrator import RuntimeContext, emit_audit
from soc_agent.application.policy_gate import can_emit_proposal, evaluate_before_proposal
from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.approval import approval_status_from_record
from soc_agent.domain.common import classification, consulted_source, data_sufficiency, hypotheses, hypothesis, make_trace, utc_now_iso
from soc_agent.domain.containment import has_complete_rollback, is_target_ambiguous, validate_containment_proposal
from soc_agent.domain.policy import build_policy_request
from soc_agent.ports.action_proposal_queue import ActionProposalQueue
from soc_agent.ports.policy_engine import PolicyEngine


class ContainmentProposalService:
    def __init__(self, policy_engine: PolicyEngine, queue: ActionProposalQueue, validator: SchemaValidator | None = None):
        self.policy_engine = policy_engine
        self.queue = queue
        self.validator = validator or SchemaValidator()

    def propose(self, incident_or_alert_ref: str, params: dict[str, Any], ctx: RuntimeContext, request_id: str | None = None, approval_record: dict[str, Any] | None = None) -> dict[str, Any]:
        req_id = request_id or f"req-{uuid4()}"
        consulted = params.get("consulted_sources") or [consulted_source("other", {"ref": incident_or_alert_ref}, "ok", utc_now_iso())]
        trace = make_trace(request_id=req_id, prompt_version=ctx.prompt_version, agent_version=ctx.agent_version)
        target = params.get("target") or {}
        if not isinstance(target, dict):
            target = {}
        # normalize to contract shape; ambiguous targets become blocked later
        normalized_target = {
            "identifier": str(target.get("identifier") or target.get("asset_id") or target.get("id") or target.get("account_id") or "unknown-target"),
            "type": str(target.get("type") or params.get("target_type") or "unknown"),
            "unambiguous": target.get("unambiguous") is True and not target.get("ambiguous"),
            "attributes": target.get("attributes") or {},
        }
        if target.get("ambiguous") is True or not (target.get("identifier") or target.get("asset_id") or target.get("id") or target.get("account_id")):
            normalized_target["unambiguous"] = False
            normalized_target["identifier"] = str(target.get("identifier") or "ambiguous-target")
            normalized_target["type"] = str(target.get("type") or "ambiguous")

        rb = params.get("rollback_plan") or {}
        steps = rb.get("steps") if isinstance(rb.get("steps"), list) and rb.get("steps") else []
        if not steps:
            steps = ["BLOQUEADO: rollback não definido (R5). Nenhuma ação deve ser executada."]
        limitations = rb.get("limitations") if isinstance(rb.get("limitations"), list) else ([str(rb.get("limitations"))] if rb.get("limitations") else [])
        if not limitations:
            limitations = ["Rollback incompleto ou ausente; proposta não acionável sem plano válido."]
        normalized_rb = {
            "summary": str(rb.get("summary") or "Rollback ausente/incompleto; proposta bloqueada para escalonamento (R5)."),
            "preconditions": rb.get("preconditions") if isinstance(rb.get("preconditions"), list) else ([str(rb.get("preconditions"))] if rb.get("preconditions") else ["N/A - rollback não definido"]),
            "steps": steps,
            "responsible": str(rb.get("responsible") or rb.get("responsible_roles") or "indefinido - requer definição humana"),
            "validation": str(rb.get("validation") or "impossível validar sem rollback definido"),
            "limitations": limitations,
        }
        proposal: dict[str, Any] = {
            "proposal_id": f"cp-{uuid4()}",
            "incident_or_alert_ref": incident_or_alert_ref,
            "action_category": params.get("action_category", "host"),
            "target": normalized_target,
            "classification": classification("proposta_contencao", "Proposta de contenção (recomendação) sujeita a aprovação humana explícita; nenhuma execução automática (R2)."),
            "confidence": params.get("confidence", "low"),
            "consulted_sources": consulted,
            "rollback_plan": normalized_rb,
            "approval_requirement": {"requires_human_approval": True, "identified_approver_required": True, "execution_permitted": False, "note": "Aprovação explícita registrada é obrigatória; ausência não implica aprovação."},
            "approval_status": "pending",
            "hypotheses": params.get("hypotheses") or hypotheses(
                primary=hypothesis("Contenção pode reduzir risco", "Evidências indicam possível benefício de contenção controlada.", False),
                alternatives=[hypothesis("Falso positivo", "A atividade pode ser benigna; contenção pode impactar indevidamente.", True)],
            ),
            "data_sufficiency": params.get("data_sufficiency") or data_sufficiency(False, known=["referencia_recebida"], missing=["validacao_completa_de_alvo_e_impacto"], escalation_required=True, escalation_reason="Dados insuficientes ou não validados para ação acionável."),
            "trace": trace,
        }
        proposal["approval_status"] = approval_status_from_record(approval_record, proposal["proposal_id"], "containment")
        target_ambiguous = is_target_ambiguous(proposal)
        rollback_ok = has_complete_rollback(proposal)
        data_sufficient = bool(proposal.get("data_sufficiency", {}).get("sufficient"))

        # force safe status in ambiguous/invalid cases
        if target_ambiguous or not rollback_ok or not data_sufficient:
            proposal["approval_status"] = "blocked"
            proposal["data_sufficiency"]["escalation_required"] = True

        policy_req = build_policy_request(
            request_id=req_id,
            proposal_kind="containment",
            candidate=proposal,
            context={
                "target_ambiguous": target_ambiguous,
                "data_sufficient": data_sufficient,
                "rollback_documented": rollback_ok,
                "has_explicit_approval_record": False,  # emission/finalization check; execution remains separate
                "has_false_positive_alternative": any(h.get("is_false_positive") for h in proposal.get("hypotheses", {}).get("alternatives", [])),
            },
        )
        decision = evaluate_before_proposal(self.policy_engine, policy_req)
        proposal["policy_decision"] = decision
        proposal["trace"]["policy_version"] = decision.get("policy_version")
        if decision.get("result") == "block_and_escalate":
            proposal["approval_status"] = "blocked"
        validate_containment_proposal(proposal)
        self.validator.validate("containment-proposal.schema.json", proposal)
        self.queue.enqueue(proposal)
        emit_audit(ctx, "containment_proposal_created", {"ref": incident_or_alert_ref, "action_category": proposal.get("action_category")}, "Proposta de contenção gerada (sem execução) com PolicyEngine antes da emissão/finalização.", {"proposal_id": proposal["proposal_id"], "approval_status": proposal["approval_status"]}, consulted_sources=consulted, confidence=proposal.get("confidence"), policy_version=decision.get("policy_version"), correlation_refs=[proposal["proposal_id"], incident_or_alert_ref], trace=trace)
        return proposal
