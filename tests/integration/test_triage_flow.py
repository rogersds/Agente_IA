from __future__ import annotations

import json
from pathlib import Path

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.application.triage_service import TriageService


def test_triage_basic_flow_produces_trace_and_audit(tmp_path):
    alert = json.loads(Path("tests/fixtures/alerts/r1_injection.json").read_text(encoding="utf-8"))
    # use benign alert variant
    alert["content"] = {"message": "login suspeito", "src_ip": "10.0.0.1"}
    sink = LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl")
    ctx = RuntimeContext(audit_sink=sink)
    result = TriageService().triage_alert(alert, ctx)
    assert result["triage_id"]
    assert result["trace"]["request_id"]
    assert isinstance(result["consulted_sources"], list)
    assert "classification" in result
    events = sink.read_all()
    assert len(events) >= 1
    assert events[0]["event_type"]
    assert "input_summary" in events[0]
    assert "outcome" in events[0]
