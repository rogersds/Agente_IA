from __future__ import annotations

from typing import Any

from soc_agent.application.orchestrator import RuntimeContext, emit_audit
from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.approval import approval_status_from_record, validate_approval_record
from soc_agent.ports.action_proposal_queue import ActionProposalQueue


class ApprovalService:
    def __init__(self, queue: ActionProposalQueue, validator: SchemaValidator | None = None):
        self.queue = queue
        self.validator = validator or SchemaValidator()

    def record_decision(self, approval_record: dict[str, Any], ctx: RuntimeContext) -> dict[str, Any]:
        """Register explicit approval/rejection linked to a proposal. Never executes actions."""
        validate_approval_record(approval_record)
        self.validator.validate("approval-record.schema.json", approval_record)
        proposal_id = approval_record["proposal_id"]
        proposal_type = approval_record["proposal_type"]
        status = approval_status_from_record(approval_record, proposal_id, proposal_type)
        # update queue metadata/state only; no execution path
        update = {"proposal_id": proposal_id, "approval_record": approval_record}
        if proposal_type == "containment":
            update["approval_status"] = status
        else:
            # query_execution approval state tracked; still requires separate controlled execution outside agent
            update["approval_status"] = status
        self.queue.update_status(update)
        emit_audit(
            ctx,
            "approval_recorded",
            {"proposal_id": proposal_id, "proposal_type": proposal_type},
            "Registro explícito de decisão humana vinculado à proposta (sem execução automática).",
            {"decision": approval_record.get("decision"), "status": status},
            correlation_refs=[proposal_id, approval_record.get("approval_id", "")],
        )
        return {"status": "recorded", "proposal_id": proposal_id, "approval_status": status}
