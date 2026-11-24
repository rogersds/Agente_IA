from __future__ import annotations

import json
from pathlib import Path

import pytest

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.application.correlation_service import CorrelationService
from soc_agent.application.orchestrator import RuntimeContext


def _ctx(tmp_path: Path) -> RuntimeContext:
    return RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit-us2.jsonl"))


def _has_false_positive_alternative(result: dict) -> bool:
    alts = (result.get("hypotheses") or {}).get("alternatives") or []
    return any(a.get("is_false_positive") is True for a in alts)


def _assert_trace_and_refs(result: dict):
    trace = result.get("trace") or {}
    assert trace.get("request_id")
    assert trace.get("created_at")
    assert isinstance(result.get("related_alerts"), list) and len(result.get("related_alerts")) >= 1
    # B.1: vínculo alerta↔incidente/correlação deve ser rastreável no artefato (related_alerts) e,
    # quando aplicável, em correlation_refs de auditoria; justificativa de equivalência:
    # correlation_refs é campo de AuditEvent (R6/data-model) enquanto CorrelationResult usa related_alerts+trace.


def _assert_timeline_ordered_and_traceable(result: dict):
    timeline = result.get("timeline") or []
    assert isinstance(timeline, list) and len(timeline) >= 1
    stamps = [e.get("timestamp") for e in timeline]
    assert all(stamps), "cada evento da linha do tempo deve ter timestamp"
    assert stamps == sorted(stamps), "linha do tempo deve estar ordenada"
    for e in timeline:
        assert e.get("event_ref"), "evento deve referenciar alerta/evidência de origem"
        assert e.get("source") or e.get("capability") or e.get("origin"), "evento deve ter origem rastreável"


def test_us2_correlation_probable_relation_by_shared_asset_has_grouping_timeline_and_fp_alternative(tmp_path):
    """T032/B.1.b: relação provável (ativo comum), escopo sob demanda, timeline, hipótese alt. incl. falso positivo."""
    scope = {
        "requested_by": "SYNTH-ANALYST-01",
        "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T02:00:00Z"},
        "assets": ["SYNTH-HOST-01"],
        "request_channel": "on_demand",
    }
    items = [
        {"alert_id": "SYNTH-ALERT-A1", "timestamp": "2026-01-01T00:10:00Z", "asset": "SYNTH-HOST-01", "source": "SYNTH-SRC-SIEM", "message": "SYNTH-EVENT-LOGIN"},
        {"alert_id": "SYNTH-ALERT-A2", "timestamp": "2026-01-01T00:20:00Z", "asset": "SYNTH-HOST-01", "source": "SYNTH-SRC-EDR", "message": "SYNTH-EVENT-PROC"},
    ]
    ctx = _ctx(tmp_path)
    result = CorrelationService().correlate(scope, items, ctx, request_id="SYNTH-REQ-CORR-FLOW-01")

    assert result["scope"].get("request_channel") == "on_demand" or result["scope"].get("requested_by")
    assert set(result["related_alerts"]) == {"SYNTH-ALERT-A1", "SYNTH-ALERT-A2"}
    assert result["classification"]["label"] not in {"indeterminado"}
    assert result["confidence"] is not None
    assert isinstance(result.get("consulted_sources"), list) and len(result["consulted_sources"]) >= 1
    assert all(s.get("consulted_at") for s in result["consulted_sources"])
    assert _has_false_positive_alternative(result)
    _assert_trace_and_refs(result)
    _assert_timeline_ordered_and_traceable(result)
    grouping = result.get("grouping") or {}
    assert "SYNTH-HOST-01" in (grouping.get("by_asset") or grouping.get("assets") or [])

    events = ctx.audit_sink.read_all()
    assert any(e.get("event_type") == "correlation_completed" for e in events)
    corr_events = [e for e in events if e.get("event_type") == "correlation_completed"]
    assert corr_events and "SYNTH-ALERT-A1" in (corr_events[-1].get("correlation_refs") or [])


def test_us2_correlation_insufficient_signals_indeterminate_escalates_without_causal_claim(tmp_path):
    """T032/R4: sinais insuficientes => indeterminado, escalonamento, lacunas explícitas, sem relação causal inventada."""
    scope = {"requested_by": "SYNTH-ANALYST-01", "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}}
    items = [{"alert_id": "SYNTH-ALERT-SOLO", "timestamp": "2026-01-01T00:10:00Z", "source": "SYNTH-SRC-SIEM"}]
    result = CorrelationService().correlate(scope, items, _ctx(tmp_path), request_id="SYNTH-REQ-CORR-FLOW-02")

    assert result["classification"]["label"] == "indeterminado"
    assert result["data_sufficiency"]["sufficient"] is False
    assert result["data_sufficiency"]["escalation_required"] is True
    assert result["data_sufficiency"].get("missing"), "deve explicitar evidências/lacunas faltantes"
    assert _has_false_positive_alternative(result)
    assert "correlacao_possivel" != result["classification"]["label"]
    _assert_trace_and_refs(result)
    gaps = result.get("telemetry_gaps") or result["data_sufficiency"].get("missing") or []
    assert len(gaps) >= 1


def test_us2_correlation_multiple_unlinked_signals_does_not_invent_link_r4(tmp_path):
    """B.1.b/c: múltiplos sinais sem evidência de ligação => não afirmar correlação; indeterminado/escalonado (R4)."""
    scope = {"requested_by": "SYNTH-ANALYST-01", "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T03:00:00Z"}}
    items = [
        {"alert_id": "SYNTH-ALERT-U1", "timestamp": "2026-01-01T00:10:00Z", "asset": "SYNTH-HOST-01", "user": "SYNTH-USER-01", "source": "SYNTH-SRC-A"},
        {"alert_id": "SYNTH-ALERT-U2", "timestamp": "2026-01-01T02:50:00Z", "asset": "SYNTH-HOST-99", "user": "SYNTH-USER-99", "source": "SYNTH-SRC-B"},
    ]
    result = CorrelationService().correlate(scope, items, _ctx(tmp_path), request_id="SYNTH-REQ-CORR-FLOW-03")

    assert result["classification"]["label"] == "indeterminado"
    assert result["data_sufficiency"]["escalation_required"] is True
    assert _has_false_positive_alternative(result)
    assert result["confidence"] in {"low", "unknown"} or result["data_sufficiency"]["sufficient"] is False
    _assert_trace_and_refs(result)
    # não deve apresentar correlação como fato quando não há âncora/evidência de ligação
    assert "confirmada" not in (result["classification"].get("justification") or "").lower()


def test_us2_correlation_contradictory_signals_escalate_with_alternatives(tmp_path):
    """T032/R4: sinais contraditórios/insuficientes para conclusão => indeterminado, hipóteses alternativas incl. FP."""
    scope = {"requested_by": "SYNTH-ANALYST-01", "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}, "assets": ["SYNTH-HOST-01"]}
    items = [
        {"alert_id": "SYNTH-ALERT-C1", "timestamp": "2026-01-01T00:10:00Z", "asset": "SYNTH-HOST-01", "verdict": "malicious", "source": "SYNTH-SRC-A"},
        {"alert_id": "SYNTH-ALERT-C2", "timestamp": "2026-01-01T00:11:00Z", "asset": "SYNTH-HOST-01", "verdict": "benign", "source": "SYNTH-SRC-B"},
    ]
    result = CorrelationService().correlate(scope, items, _ctx(tmp_path), request_id="SYNTH-REQ-CORR-FLOW-04")

    assert result["classification"]["label"] == "indeterminado"
    assert _has_false_positive_alternative(result)
    assert result["data_sufficiency"]["escalation_required"] is True
    alts = result["hypotheses"]["alternatives"]
    assert len(alts) >= 1
    _assert_trace_and_refs(result)


def test_us2_correlation_normalizes_heterogeneous_inputs_and_missing_optional_fields(tmp_path):
    """B.1.b: entradas heterogêneas (ids/campos distintos, opcionais ausentes) normalizadas com rastreabilidade."""
    scope = {"requested_by": "SYNTH-ANALYST-01", "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}, "assets": ["SYNTH-HOST-02"]}
    items = [
        {"id": "SYNTH-ALTID-1", "timestamp": "2026-01-01T00:10:00Z", "asset": "SYNTH-HOST-02", "source": "SYNTH-SRC-X"},
        {"evidence_id": "SYNTH-EVID-2", "time": "2026-01-01T00:12:00Z", "host": "SYNTH-HOST-02", "origin": "SYNTH-SRC-Y"},
        {"alert_id": "SYNTH-ALERT-3", "asset": "SYNTH-HOST-02"},  # timestamp ausente/opcional
    ]
    result = CorrelationService().correlate(scope, items, _ctx(tmp_path), request_id="SYNTH-REQ-CORR-FLOW-05")

    assert "SYNTH-ALTID-1" in result["related_alerts"]
    assert "SYNTH-EVID-2" in result["related_alerts"]
    assert "SYNTH-ALERT-3" in result["related_alerts"]
    _assert_trace_and_refs(result)
    assert isinstance(result.get("consulted_sources"), list) and len(result["consulted_sources"]) >= 1
    # normalização não deve remover necessidade de hipóteses/FP
    assert _has_false_positive_alternative(result)
    # se não houver evidência temporal completa, deve explicitar lacuna/limitação
    assert result.get("telemetry_gaps") is not None or result["data_sufficiency"].get("missing") is not None
