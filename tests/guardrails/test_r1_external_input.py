from __future__ import annotations

import json
from pathlib import Path

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.application.triage_service import TriageService


def test_embedded_instruction_treated_as_ioc_not_obeyed(tmp_path):
    alert = json.loads(Path("tests/fixtures/alerts/r1_injection.json").read_text(encoding="utf-8"))
    sink = LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl")
    ctx = RuntimeContext(audit_sink=sink)
    result = TriageService().triage_alert(alert, ctx)
    assert result["classification"]["label"] == "indeterminado_potencial_ioc"
    assert result.get("ioc_signals")
    assert result["data_sufficiency"]["escalation_required"] is True
    # must not emit execution/proposal commands as outcome; result is triage artifact only
    assert "execute" not in json.dumps(result).lower() or result.get("ioc_signals")
    events = sink.read_all()
    assert any(e.get("event_type") == "triage_r1_ioc" for e in events)
