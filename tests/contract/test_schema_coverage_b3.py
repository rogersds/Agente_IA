from __future__ import annotations

"""B.3: cobertura adicional dos 21 schemas (campos opcionais ausentes, $ref, normalizações).

Este arquivo complementa `tests/contract/test_schema_validation.py`, `test_us2_correlation_contracts.py`,
`test_us3_query_proposal_contracts.py`, `test_us4_containment_contracts.py` e `test_policy_decision_equivalence_b0.py`.
Equivalências: shapes de triage/correlação/query/containment/approval/audit também validados em fluxos e guardrails;
policy request/response exercitados com OPA real em B.0. (R3: sentinelas sintéticas apenas.)
"""

import pytest

from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.common import classification, consulted_source, data_sufficiency, hypotheses, hypothesis, make_trace, utc_now_iso


v = SchemaValidator()
TS = "2026-01-01T00:00:00Z"
TRACE = make_trace(request_id="SYNTH-REQ-B3", agent_version="0.1.0", prompt_version="prompt-v1")
POLICY = {
    "decision_id": "SYNTH-PD-01",
    "policy_id": "soc_agent.policy.action_proposal",
    "policy_version": "v1",
    "evaluated_at": TS,
    "input_ref": {"request_id": "SYNTH-REQ-B3", "proposal_kind": "query_proposal"},
    "result": "allow_proposal",
    "reasons": ["SYNTH-OK"],
}


def base_common():
    return {
        "classification": classification("indeterminado", "SYNTH-JUST"),
        "confidence": "low",
        "consulted_sources": [consulted_source("other", {"ref": "SYNTH"}, "ok", TS)],
        "data_sufficiency": data_sufficiency(False, known=["SYNTH-K"], missing=["SYNTH-M"], escalation_required=True, escalation_reason="SYNTH-ESC"),
        "hypotheses": hypotheses(hypothesis("SYNTH-H", "SYNTH-R", False), [hypothesis("SYNTH-FP", "SYNTH-R", True)]),
        "trace": TRACE,
    }


CASES = [
    ("common.schema.json", {
        # common itself is $defs-based; validate via a wrapper usage through triage-result in other tests, but also ensure refs resolve by validating instances that use them
        # Not directly a root object schema; covered by $ref usage. Placeholder handled separately.
    }),
]


def test_common_schema_refs_exercised_via_instances():
    """common.schema.json: $defs/$ref exercitados (consultedSource sem source_id opcional, hypotheses, trace)."""
    c = base_common()
    # normalização: consultedSource sem source_id/details opcionais
    c["consulted_sources"] = [{"capability": "alert_source", "reference": {"id": "SYNTH"}, "status": "unavailable", "consulted_at": TS}]
    v.validate("triage-result.schema.json", {"triage_id": "SYNTH-T1", "alert_id": "SYNTH-A1", **c})


def test_triage_result_optional_fields_absent():
    inst = {"triage_id": "SYNTH-T1", "alert_id": "SYNTH-A1", **base_common()}
    inst["data_sufficiency"] = data_sufficiency(True, ["k"], [], False)
    v.validate("triage-result.schema.json", inst)


def test_correlation_result_optional_escalation_absent_and_extra_allowed():
    inst = {
        "correlation_id": "SYNTH-C1",
        "scope": {"requested_by": "SYNTH", "period": {"start": TS, "end": "2026-01-01T01:00:00Z"}},
        "related_alerts": ["SYNTH-A1"],
        "classification": classification("indeterminado", "SYNTH"),
        "confidence": "low",
        "consulted_sources": [consulted_source("other", {"scope": 1}, "ok", TS)],
        "data_sufficiency": data_sufficiency(False, ["k"], ["m"], True, "SYNTH"),
        "hypotheses": hypotheses(hypothesis("h", "r"), [hypothesis("fp", "r", True)]),
        "trace": TRACE,
        # opcionais/extra: escalation ausente, timeline/grouping presentes
        "timeline": [{"event_ref": "SYNTH-A1", "source": "SYNTH", "timestamp": TS}],
    }
    v.validate("correlation-result.schema.json", inst)


def test_query_proposal_with_optional_null_fields_and_justification():
    inst = {
        "query_proposal_id": "SYNTH-Q1",
        "objective": "SYNTH",
        "classification": classification("proposta_consulta", "SYNTH"),
        "confidence": "low",
        "consulted_sources": [consulted_source("other", {"x": 1}, "ok", TS)],
        "time_window": None,
        "data_scope": None,
        "cost_estimate": None,
        "parameter_justification": "SYNTH-R7-JUST",
        "query_artifact": "SYNTH-ART",
        "execution_status": "blocked",
        "requires_human_review": True,
        "hypotheses": hypotheses(hypothesis("h", "r"), [hypothesis("fp", "r", True)]),
        "data_sufficiency": data_sufficiency(False, ["k"], ["m"], True, "SYNTH"),
        "policy_decision": {**POLICY, "result": "block_and_escalate"},
        "trace": TRACE,
    }
    v.validate("query-proposal.schema.json", inst)


def test_containment_proposal_minimal_optional_absent():
    inst = {
        "proposal_id": "SYNTH-P1",
        "incident_or_alert_ref": "SYNTH-REF",
        "action_category": "identity_account",
        "target": {"identifier": "SYNTH-T", "type": "account", "unambiguous": True},
        "classification": classification("proposta_contencao", "SYNTH"),
        "confidence": "low",
        "consulted_sources": [consulted_source("other", {"x": 1}, "ok", TS)],
        "rollback_plan": {"summary": "SYNTH", "steps": ["SYNTH"], "responsible": "SYNTH", "validation": "SYNTH", "limitations": []},
        "approval_requirement": {"requires_human_approval": True, "identified_approver_required": True, "execution_permitted": False},
        "approval_status": "blocked",
        "hypotheses": hypotheses(hypothesis("h", "r"), [hypothesis("fp", "r", True)]),
        "data_sufficiency": data_sufficiency(False, ["k"], ["m"], True, "SYNTH"),
        "policy_decision": {**POLICY, "result": "block_and_escalate"},
        "trace": TRACE,
    }
    v.validate("containment-proposal.schema.json", inst)


def test_approval_record_optional_notes_absent():
    v.validate("approval-record.schema.json", {
        "approval_id": "SYNTH-APR",
        "proposal_id": "SYNTH-P",
        "proposal_type": "query_execution",
        "approver": {"id": "SYNTH-U", "display_name": "SYNTH USER"},
        "decision": "rejected",
        "scope": {},
        "decided_at": TS,
    })


def test_audit_event_optional_fields_absent():
    v.validate("audit-event.schema.json", {
        "audit_id": "SYNTH-AUD",
        "event_type": "generic",
        "occurred_at": TS,
        "input_summary": {"x": 1},
        "reasoning_summary": "SYNTH",
        "outcome": {"ok": True},
    })


def test_audit_request_response_variants():
    v.validate("audit.request.schema.json", {"operation": "append", "requested_at": TS, "event": {"audit_id": "SYNTH-AUD", "event_type": "generic", "occurred_at": TS, "input_summary": {"x": 1}, "reasoning_summary": "SYNTH", "outcome": {"ok": True}}})
    v.validate("audit.request.schema.json", {"operation": "query", "requested_at": TS, "query": {"correlation_refs": ["SYNTH"]}})
    v.validate("audit.response.schema.json", {"operation": "append", "status": "ok", "completed_at": TS, "audit_id": "SYNTH-AUD"})
    v.validate("audit.response.schema.json", {"operation": "query", "status": "ok", "completed_at": TS, "events": []})
    v.validate("audit.response.schema.json", {"operation": "query", "status": "error", "completed_at": TS, "message": "SYNTH-ERR"})


def test_policy_decision_request_response_variants():
    # proposal_kind conforme contrato; request_id não é obrigatório no schema mas usado na prática
    v.validate("policy-decision.request.schema.json", {
        "request_id": "SYNTH-REQ",
        "proposal_kind": "query_proposal",
        "candidate": {"id": "SYNTH"},
        "context": {"data_sufficient": True},
        "requested_at": TS,
    })
    v.validate("policy-decision.request.schema.json", {
        "request_id": "SYNTH-REQ-2",
        "proposal_kind": "containment",
        "candidate": {},
        "context": {},
        "requested_at": TS,
    })
    for result in ("allow_proposal", "require_revision", "block_and_escalate"):
        v.validate("policy-decision.response.schema.json", {
            "decision_id": "SYNTH-PD",
            "policy_id": "soc_agent.policy.action_proposal",
            "policy_version": "v1",
            "evaluated_at": TS,
            "input_ref": {"request_id": "SYNTH-REQ", "proposal_kind": "containment"},
            "result": result,
            "reasons": ["SYNTH"],
            "required_actions": ["SYNTH-ACTION"] if result != "allow_proposal" else [],
        })


def test_action_proposal_queue_request_response_variants():
    qp = {"query_proposal_id": "SYNTH-Q"}
    v.validate("action-proposal-queue.request.schema.json", {"operation": "enqueue", "requested_at": TS, "proposal": qp})
    v.validate("action-proposal-queue.request.schema.json", {"operation": "get", "requested_at": TS, "proposal_id": "SYNTH-Q"})
    v.validate("action-proposal-queue.request.schema.json", {"operation": "update_status", "requested_at": TS, "status_update": {"proposal_id": "SYNTH-Q", "new_status": "blocked"}})
    for op, status in (("enqueue", "ok"), ("get", "not_found"), ("update_status", "rejected"), ("get", "error")):
        v.validate("action-proposal-queue.response.schema.json", {"operation": op, "status": status, "completed_at": TS})


def test_alert_source_request_response_variants():
    v.validate("alert-source.request.schema.json", {"operation": "get_alert", "requested_at": TS, "alert_id": "SYNTH-A"})
    v.validate("alert-source.request.schema.json", {"operation": "fetch_alerts", "requested_at": TS, "filters": {"since": TS}, "time_window": {"start": TS, "end": "2026-01-01T01:00:00Z"}})
    v.validate("alert-source.response.schema.json", {"status": "ok", "consulted_at": TS, "alerts": [{"alert_id": "SYNTH-A", "source": {"name": "SYNTH-SRC"}, "received_at": TS, "content": {"msg": "SYNTH"}}]})
    v.validate("alert-source.response.schema.json", {"status": "partial", "consulted_at": TS, "alerts": []})
    v.validate("alert-source.response.schema.json", {"status": "unavailable", "consulted_at": TS, "alerts": [], "error": {"reason": "SYNTH"}})


def test_search_backend_request_response_variants():
    v.validate("search-backend.request.schema.json", {"request_id": "SYNTH", "objective": "SYNTH", "requested_at": TS})
    v.validate("search-backend.response.schema.json", {"request_id": "SYNTH", "status": "partial", "consulted_at": TS, "estimated_cost": None})


def test_enrichment_request_response_variants():
    v.validate("enrichment.request.schema.json", {"request_id": "SYNTH", "subjects": [{"type": "host", "value": "SYNTH"}], "requested_at": TS})
    v.validate("enrichment.response.schema.json", {"request_id": "SYNTH", "status": "ok", "consulted_at": TS, "enrichments": [{"subject": "SYNTH", "data": {}}]})
    v.validate("enrichment.response.schema.json", {"request_id": "SYNTH", "status": "error", "consulted_at": TS, "enrichments": [], "error": {"message": "SYNTH"}})


def test_threat_intel_request_response_variants():
    v.validate("threat-intel.request.schema.json", {"request_id": "SYNTH", "indicators": [{"value": "SYNTH", "type": "ip"}], "requested_at": TS})
    v.validate("threat-intel.response.schema.json", {"request_id": "SYNTH", "status": "ok", "consulted_at": TS, "matches": []})
    v.validate("threat-intel.response.schema.json", {"request_id": "SYNTH", "status": "unavailable", "consulted_at": TS, "matches": []})


def test_llm_request_response_variants():
    v.validate("llm.request.schema.json", {"request_id": "SYNTH", "operation": "generate", "input": {"instructions": "SYNTH", "data": {"x": 1}}, "requested_at": TS})
    v.validate("llm.request.schema.json", {"request_id": "SYNTH", "operation": "analyze", "input": {"instructions": "SYNTH", "data": "SYNTH"}, "constraints": {"read_only": True}, "requested_at": TS})
    v.validate("llm.response.schema.json", {"request_id": "SYNTH", "status": "ok", "completed_at": TS, "model_version": "SYNTH-M", "prompt_version": "SYNTH-P", "output": {"summary": "SYNTH"}})
    v.validate("llm.response.schema.json", {"request_id": "SYNTH", "status": "error", "completed_at": TS, "model_version": "SYNTH-M", "prompt_version": "SYNTH-P", "error": {"message": "SYNTH"}})
