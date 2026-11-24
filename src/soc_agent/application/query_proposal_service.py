from __future__ import annotations

from typing import Any
from uuid import uuid4

from soc_agent.application.orchestrator import RuntimeContext, emit_audit
from soc_agent.application.policy_gate import can_emit_proposal, evaluate_before_proposal
from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.common import classification, consulted_source, data_sufficiency, hypotheses, hypothesis, make_trace, utc_now_iso
from soc_agent.domain.policy import build_policy_request
from soc_agent.domain.query_proposal import query_parameters_complete, validate_query_proposal
from soc_agent.ports.action_proposal_queue import ActionProposalQueue
from soc_agent.ports.policy_engine import PolicyEngine


class QueryProposalService:
    def __init__(self, policy_engine: PolicyEngine, queue: ActionProposalQueue, validator: SchemaValidator | None = None):
        self.policy_engine = policy_engine
        self.queue = queue
        self.validator = validator or SchemaValidator()

    def propose(self, objective: str, params: dict[str, Any], ctx: RuntimeContext, request_id: str | None = None) -> dict[str, Any]:
        req_id = request_id or f"req-{uuid4()}"
        consulted = [consulted_source("other", {"objective": objective}, "ok", utc_now_iso())]
        trace = make_trace(request_id=req_id, prompt_version=ctx.prompt_version, agent_version=ctx.agent_version)
        complete = query_parameters_complete({"time_window": params.get("time_window"), "data_scope": params.get("data_scope"), "cost_estimate": params.get("cost_estimate")})
        missing_params = [k for k in ["time_window", "data_scope", "cost_estimate"] if not params.get(k)]
        proposal: dict[str, Any] = {
            "query_proposal_id": f"qp-{uuid4()}",
            "objective": objective,
            "classification": classification("proposta_consulta", "Consulta proposta como artefato revisável (R7), sem execução automática."),
            "confidence": "medium",
            "consulted_sources": consulted,
            "time_window": params.get("time_window"),
            "data_scope": params.get("data_scope"),
            "cost_estimate": params.get("cost_estimate"),
            "parameter_justification": params.get("parameter_justification")
            or ("Parâmetros de consulta completos para revisão humana." if complete else f"Parâmetros ausentes ou parciais ({', '.join(missing_params)}); proposta requer revisão/bloqueio conforme R7."),
            "query_artifact": params.get("query_artifact") or {"language": "kql-or-equivalent", "text": params.get("text", "")},
            "execution_status": "proposed",
            "requires_human_review": True,
            "hypotheses": hypotheses(
                primary=hypothesis("Consulta útil para investigação", "Parâmetros propostos apoiam validação da hipótese.", False),
                alternatives=[hypothesis("Falso positivo/hipótese alternativa", "Resultados podem não confirmar a hipótese principal.", True)],
            ),
            "data_sufficiency": data_sufficiency(
                sufficient=complete,
                known=["objetivo_informado"],
                missing=missing_params,
                escalation_required=not complete,
                escalation_reason=None if complete else "Parâmetros obrigatórios de consulta incompletos (R7).",
            ),
            "trace": trace,
        }
        if proposal["data_sufficiency"]["escalation_required"]:
            proposal["execution_status"] = "blocked"

        policy_req = build_policy_request(
            request_id=req_id,
            proposal_kind="query_proposal",
            candidate=proposal,
            context={
                "query_parameters_complete": query_parameters_complete(proposal),
                "has_explicit_approval_record": False,
                "data_sufficient": not proposal["data_sufficiency"]["escalation_required"],
            },
        )
        decision = evaluate_before_proposal(self.policy_engine, policy_req)
        proposal["policy_decision"] = decision
        proposal["trace"]["policy_version"] = decision.get("policy_version")
        if decision.get("result") == "block_and_escalate":
            proposal["execution_status"] = "blocked"
        else:
            # allow_proposal/require_revision still require human review; never execute
            proposal["execution_status"] = "pending_review"
        validate_query_proposal(proposal)
        self.validator.validate("query-proposal.schema.json", proposal)
        self.queue.enqueue(proposal)
        emit_audit(ctx, "query_proposal_created", {"objective": objective}, "Proposta de consulta gerada com avaliação de PolicyEngine antes da emissão/finalização.", {"query_proposal_id": proposal["query_proposal_id"], "execution_status": proposal["execution_status"]}, consulted_sources=consulted, confidence=proposal.get("confidence"), policy_version=decision.get("policy_version"), correlation_refs=[proposal["query_proposal_id"]], trace=trace)
        return proposal
