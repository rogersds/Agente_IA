from __future__ import annotations

import json
from pathlib import Path

import pytest

from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.approval import build_approval_record
from soc_agent.domain.audit import build_audit_event
from soc_agent.domain.common import classification, consulted_source, data_sufficiency, hypotheses, hypothesis, make_trace, utc_now_iso


@pytest.fixture()
def validator():
    return SchemaValidator()


def minimal_triage():
    trace = make_trace(request_id="r1", agent_version="0.1.0")
    return {
        "triage_id": "t1",
        "alert_id": "a1",
        "classification": classification("suspeito", "teste"),
        "confidence": "medium",
        "consulted_sources": [consulted_source("alert_source", {"id": "a1"}, "ok", utc_now_iso())],
        "data_sufficiency": data_sufficiency(True, known=["x"], missing=[]),
        "hypotheses": hypotheses(hypothesis("h", "r", False), [hypothesis("fp", "r", True)]),
        "trace": trace,
    }


def test_triage_schema(validator):
    validator.validate("triage-result.schema.json", minimal_triage())


def test_audit_schema(validator):
    ev = build_audit_event("triage", {"a": 1}, "r", {"o": 1})
    validator.validate("audit-event.schema.json", ev)


def test_approval_schema(validator):
    rec = build_approval_record("ap1", "p1", "containment", "approved", "human-1", "ok")
    validator.validate("approval-record.schema.json", rec)


def test_query_proposal_schema_shape(validator):
    trace = make_trace(request_id="r1")
    proposal = {
        "query_proposal_id": "q1",
        "objective": "investigar",
        "classification": classification("proposta", "j"),
        "confidence": "low",
        "consulted_sources": [consulted_source("other", {"x": 1}, "ok", utc_now_iso())],
        "time_window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
        "data_scope": {"sources": ["logs"]},
        "cost_estimate": {"summary": "estimativa baixa", "estimated_scan_units": 10},
        "parameter_justification": "Janela, escopo e custo estimados para revisão humana.",
        "query_artifact": {"text": "select 1", "version": "1"},
        "execution_status": "pending_review",
        "requires_human_review": True,
        "hypotheses": hypotheses(hypothesis("h", "r", False), [hypothesis("fp", "r", True)]),
        "data_sufficiency": data_sufficiency(True, ["k"], []),
        "policy_decision": {
            "decision_id": "pd-1",
            "policy_id": "soc_agent.policy.action_proposal",
            "policy_version": "v1",
            "evaluated_at": utc_now_iso(),
            "input_ref": {"request_id": "r1", "proposal_kind": "query_proposal"},
            "result": "allow_proposal",
            "reasons": ["ok"],
        },
        "trace": trace,
    }
    validator.validate("query-proposal.schema.json", proposal)


def test_containment_proposal_schema_shape(validator):
    trace = make_trace(request_id="r1")
    proposal = {
        "proposal_id": "c1",
        "incident_or_alert_ref": "a1",
        "action_category": "host",
        "target": {"identifier": "host-1", "type": "host", "unambiguous": True},
        "classification": classification("proposta", "j"),
        "confidence": "low",
        "consulted_sources": [consulted_source("other", {"x": 1}, "ok", utc_now_iso())],
        "rollback_plan": {
            "summary": "Reverter isolamento",
            "preconditions": ["acesso administrativo"],
            "steps": ["remover bloqueio"],
            "responsible": "SOC/NOC",
            "validation": "verificar conectividade e logs",
            "limitations": ["janela de manutenção"],
        },
        "approval_requirement": {"requires_human_approval": True, "identified_approver_required": True, "execution_permitted": False},
        "approval_status": "pending",
        "hypotheses": hypotheses(hypothesis("h", "r", False), [hypothesis("fp", "r", True)]),
        "data_sufficiency": data_sufficiency(True, ["k"], []),
        "policy_decision": {
            "decision_id": "pd-1",
            "policy_id": "soc_agent.policy.action_proposal",
            "policy_version": "v1",
            "evaluated_at": utc_now_iso(),
            "input_ref": {"request_id": "r1", "proposal_kind": "containment"},
            "result": "allow_proposal",
            "reasons": ["ok"],
        },
        "trace": trace,
    }
    validator.validate("containment-proposal.schema.json", proposal)
