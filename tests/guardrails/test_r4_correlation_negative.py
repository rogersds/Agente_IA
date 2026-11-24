from __future__ import annotations

from pathlib import Path

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.application.correlation_service import CorrelationService
from soc_agent.application.orchestrator import RuntimeContext


def _ctx(tmp_path: Path) -> RuntimeContext:
    return RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit-r4-corr.jsonl"))


def _has_false_positive_alternative(result: dict) -> bool:
    alts = (result.get("hypotheses") or {}).get("alternatives") or []
    return any(a.get("is_false_positive") is True for a in alts)


def test_correlation_does_not_link_alerts_by_generic_field_without_evidence(tmp_path):
    """B.1.c/R4: campo genérico compartilhado (ex.: mesma severidade/tipo genérico) NÃO é evidência de ligação."""
    scope = {"requested_by": "SYNTH-ANALYST-01", "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T04:00:00Z"}}
    items = [
        {"alert_id": "SYNTH-ALERT-G1", "timestamp": "2026-01-01T00:05:00Z", "asset": "SYNTH-HOST-10", "severity": "low", "category": "generic_event", "source": "SYNTH-SRC-A"},
        {"alert_id": "SYNTH-ALERT-G2", "timestamp": "2026-01-01T03:55:00Z", "asset": "SYNTH-HOST-77", "severity": "low", "category": "generic_event", "source": "SYNTH-SRC-B"},
    ]
    result = CorrelationService().correlate(scope, items, _ctx(tmp_path), request_id="SYNTH-REQ-CORR-NEG-01")

    assert result["classification"]["label"] == "indeterminado"
    assert result["data_sufficiency"]["escalation_required"] is True
    assert _has_false_positive_alternative(result)
    assert "SYNTH-ALERT-G1" in result["related_alerts"] and "SYNTH-ALERT-G2" in result["related_alerts"]


def test_correlation_does_not_present_single_hypothesis_as_fact_under_ambiguity(tmp_path):
    """B.1.c/R4: ambiguidade => hipótese principal não é fato único; alternativa (incl. FP) obrigatória."""
    scope = {"requested_by": "SYNTH-ANALYST-01", "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}}
    items = [
        {"alert_id": "SYNTH-ALERT-H1", "timestamp": "2026-01-01T00:10:00Z", "asset": "SYNTH-HOST-01", "source": "SYNTH-SRC-A"},
        {"alert_id": "SYNTH-ALERT-H2", "timestamp": "2026-01-01T00:11:00Z", "asset": "SYNTH-HOST-01", "source": "SYNTH-SRC-B"},
    ]
    result = CorrelationService().correlate(scope, items, _ctx(tmp_path), request_id="SYNTH-REQ-CORR-NEG-02")

    hyps = result.get("hypotheses") or {}
    assert hyps.get("primary") is not None
    assert isinstance(hyps.get("alternatives"), list) and len(hyps["alternatives"]) >= 1
    assert _has_false_positive_alternative(result)
    # não afirmar como certeza absoluta
    justification = (result.get("classification") or {}).get("justification") or ""
    assert "certeza absoluta" not in justification.lower()


def test_correlation_does_not_omit_telemetry_gaps_when_information_missing(tmp_path):
    """B.1.c/R4: lacunas de telemetria/informação ausente devem ser explicitadas."""
    scope = {"requested_by": "SYNTH-ANALYST-01", "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}}
    items = [
        {"alert_id": "SYNTH-ALERT-T1", "asset": "SYNTH-HOST-03", "source": "SYNTH-SRC-A"},  # sem timestamp
        {"evidence_id": "SYNTH-EVID-T2", "asset": "SYNTH-HOST-03", "source": "SYNTH-SRC-B"},
    ]
    result = CorrelationService().correlate(scope, items, _ctx(tmp_path), request_id="SYNTH-REQ-CORR-NEG-03")

    missing = (result.get("data_sufficiency") or {}).get("missing") or []
    gaps = result.get("telemetry_gaps") or []
    assert missing or gaps, "lacunas de telemetria/dados devem ser explicitadas quando há informação ausente"
    assert (result.get("trace") or {}).get("request_id")


def test_correlation_emits_result_with_trace_and_linkable_refs_in_audit(tmp_path):
    """B.1.c/R6: resultado deve ter trace e IDs relacionados; auditoria deve registrar refs de correlação."""
    scope = {"requested_by": "SYNTH-ANALYST-01", "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}, "assets": ["SYNTH-HOST-04"]}
    items = [
        {"alert_id": "SYNTH-ALERT-R1", "timestamp": "2026-01-01T00:10:00Z", "asset": "SYNTH-HOST-04", "source": "SYNTH-SRC-A"},
        {"alert_id": "SYNTH-ALERT-R2", "timestamp": "2026-01-01T00:11:00Z", "asset": "SYNTH-HOST-04", "source": "SYNTH-SRC-B"},
    ]
    ctx = _ctx(tmp_path)
    result = CorrelationService().correlate(scope, items, ctx, request_id="SYNTH-REQ-CORR-NEG-04")

    assert result.get("trace", {}).get("request_id") == "SYNTH-REQ-CORR-NEG-04"
    assert set(["SYNTH-ALERT-R1", "SYNTH-ALERT-R2"]).issubset(set(result.get("related_alerts") or []))
    events = ctx.audit_sink.read_all()
    corr_events = [e for e in events if e.get("event_type") == "correlation_completed"]
    assert corr_events, "evento de auditoria da correlação deve existir"
    refs = corr_events[-1].get("correlation_refs") or []
    assert "SYNTH-ALERT-R1" in refs and "SYNTH-ALERT-R2" in refs
    assert (corr_events[-1].get("trace") or {}).get("request_id") == "SYNTH-REQ-CORR-NEG-04"
