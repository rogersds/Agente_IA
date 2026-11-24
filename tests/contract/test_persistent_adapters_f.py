from __future__ import annotations

"""Fase F: testes de contrato para adapters persistentes atrás das mesmas interfaces.

Valida persistência append-only (audit/fila), conformidade operacional e ausência de execução automática.
Dados e sentinelas são sintéticos (R3).
"""

from soc_agent.adapters.audit_sink.persistent_append_only import PersistentAppendOnlyAuditSink
from soc_agent.adapters.proposal_queue.persistent_queue import PersistentActionProposalQueue
from soc_agent.domain.common import utc_now_iso


def _audit_event():
    ts = utc_now_iso()
    return {
        "audit_id": "SYNTH-AUDIT-F-1",
        "request_id": "SYNTH-REQ-F-1",
        "event_type": "triage_completed",
        "timestamp": ts,
        "operation": "triage",
        "agent_version": "0.1.0",
        "input_summary": "SYNTH",
        "consulted_sources": [{"source_type": "alert_source", "ref": {"alert_id": "SYNTH-A1"}, "status": "ok", "consulted_at": ts}],
        "reasoning_summary": "SYNTH",
        "output_summary": "SYNTH",
        "confidence": 0.5,
        "data_sufficiency": {"sufficient": True, "knowns": ["k"], "unknowns": [], "assumptions": [], "escalation_recommended": False},
        "limitations": [],
        "policy_decisions": [],
        "correlation_refs": ["SYNTH-REQ-F-1"],
        "trace": {"request_id": "SYNTH-REQ-F-1", "created_at": ts},
    }


def test_persistent_audit_sink_append_query_and_persistence(tmp_path):
    path = tmp_path / "audit.jsonl"
    sink = PersistentAppendOnlyAuditSink(path)
    evt = _audit_event()
    res = sink.append(evt)
    assert res["status"] == "appended"
    assert res["audit_id"] == "SYNTH-AUDIT-F-1"
    q = sink.query({"event_type": "triage_completed"})
    assert q["count"] >= 1
    assert any(e.get("audit_id") == "SYNTH-AUDIT-F-1" for e in q["events"])
    # recarrega do armazenamento persistente (mesma interface/semântica)
    sink2 = PersistentAppendOnlyAuditSink(path)
    assert any(e.get("audit_id") == "SYNTH-AUDIT-F-1" for e in sink2.read_all())


def test_persistent_proposal_queue_enqueue_get_update_no_execution(tmp_path):
    path = tmp_path / "queue.jsonl"
    q = PersistentActionProposalQueue(path)
    proposal = {
        "proposal_id": "SYNTH-CONT-F-1",
        "created_at": utc_now_iso(),
        "status": "pending_approval",
        "requester": {"identity": "SYNTH", "channel": "cli"},
        "action_category": "host",
        "target": {"identifier": "SYNTH-HOST", "type": "host", "unambiguous": True},
        "justification": {"incident_or_alert_ref": "SYNTH-INC", "evidence_refs": [], "rationale": "SYNTH", "alternatives_considered": []},
        "expected_impact": "SYNTH",
        "side_effects": [],
        "rollback_plan": {"summary": "S", "steps": ["s"], "responsible": "r", "validation": "v", "limitations": []},
        "confidence": 0.5,
        "data_sufficiency": {"sufficient": True, "knowns": ["k"], "unknowns": [], "assumptions": [], "escalation_recommended": False},
        "sources_consulted": [],
        "approval_requirement": {"execution_permitted": False, "approved_by": None, "approved_at": None, "approval_record_ref": None},
        "policy_decision": {"decision": "allow_proposal", "policy_version": "1.0.0", "reasons": [], "blocked_conditions": []},
    }
    er = q.enqueue(proposal)
    assert er["status"] == "ok" and er["operation"] == "enqueue"
    gr = q.get("SYNTH-CONT-F-1")
    assert gr["status"] == "ok" and gr["proposal"]["proposal_id"] == "SYNTH-CONT-F-1"
    # aprovação explícita registrada altera estado; nenhuma execução automática
    ur = q.update_status({"proposal_id": "SYNTH-CONT-F-1", "new_status": "approved", "approval_record": {"decision": "approved", "approver": "SYNTH-HUMAN"}})
    assert ur["status"] == "ok"
    final = q.get("SYNTH-CONT-F-1")["proposal"]
    assert final.get("approval_status") == "approved"
    assert final.get("approval_record", {}).get("decision") == "approved"
    # persistência: recarrega
    q2 = PersistentActionProposalQueue(path)
    assert q2.get("SYNTH-CONT-F-1")["proposal"]["approval_status"] == "approved"

