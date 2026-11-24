from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any
from uuid import uuid4

from soc_agent.application.orchestrator import RuntimeContext, emit_audit
from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.common import classification, consulted_source, data_sufficiency, hypotheses, hypothesis, make_trace, utc_now_iso
from soc_agent.domain.correlation import validate_correlation_result


_STRONG_ANCHOR_KEYS = ("asset", "host", "hostname", "ip", "src_ip", "dst_ip", "user", "account", "campaign", "campaign_id", "incident_id", "case_id")
_GENERIC_KEYS = {"severity", "category", "type", "priority", "status"}
_VERDICT_KEYS = ("verdict", "disposition", "assessment", "conclusion")
_CONTRADICTORY_VERDICTS = {
    frozenset({"malicious", "benign"}),
    frozenset({"true_positive", "false_positive"}),
    frozenset({"tp", "fp"}),
    frozenset({"bad", "good"}),
}


def _item_id(item: dict[str, Any], idx: int) -> str:
    for k in ("alert_id", "id", "evidence_id", "event_id"):
        v = item.get(k)
        if v is not None and str(v).strip():
            return str(v)
    return f"SYNTH-ITEM-{idx}"


def _extract_timestamp(item: dict[str, Any]) -> str | None:
    for k in ("timestamp", "time", "event_time", "observed_at", "@timestamp", "ts"):
        v = item.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s:
            return s
    return None


def _extract_source(item: dict[str, Any]) -> str:
    for k in ("source", "origin", "provider", "sensor", "log_source"):
        v = item.get(k)
        if v is not None and str(v).strip():
            return str(v)
    return "unknown_source"


def _normalize_verdict(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    return s or None


def _anchors_for_item(item: dict[str, Any]) -> dict[str, set[str]]:
    anchors: dict[str, set[str]] = {}
    for k in _STRONG_ANCHOR_KEYS:
        v = item.get(k)
        if v is None:
            continue
        if isinstance(v, (list, tuple, set)):
            vals = {str(x).strip() for x in v if str(x).strip()}
        else:
            vals = {str(v).strip()} if str(v).strip() else set()
        if vals:
            anchors[k] = vals
    return anchors


def _shared_strong_anchors(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    shared: dict[str, list[str]] = {}
    for key in _STRONG_ANCHOR_KEYS:
        values: list[str] = []
        for item in items:
            a = _anchors_for_item(item).get(key, set())
            values.extend(sorted(a))
        if not values:
            continue
        counts = Counter(values)
        common = [v for v, c in counts.items() if c >= 2]
        if common:
            shared[key] = sorted(common)
    return shared


def _contradiction_present(items: list[dict[str, Any]]) -> bool:
    verdicts: set[str] = set()
    for item in items:
        for k in _VERDICT_KEYS:
            if k in item:
                nv = _normalize_verdict(item.get(k))
                if nv:
                    verdicts.add(nv)
    if len(verdicts) < 2:
        return False
    for pair in _CONTRADICTORY_VERDICTS:
        if pair.issubset(verdicts):
            return True
    # generic opposite tokens
    if ("malicious" in verdicts and "clean" in verdicts) or ("suspicious" in verdicts and "benign" in verdicts):
        return True
    return False


def _timeline(items: list[dict[str, Any]], ids: list[str]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    timeline: list[dict[str, Any]] = []
    gaps: list[dict[str, str]] = []
    for idx, (item, event_ref) in enumerate(zip(items, ids)):
        ts = _extract_timestamp(item)
        src = _extract_source(item)
        entry = {
            "event_ref": event_ref,
            "source": src,
            "origin": src,
            "description": str(item.get("message") or item.get("description") or item.get("event_type") or "evento_observado"),
        }
        if ts:
            entry["timestamp"] = ts
        else:
            gaps.append({"gap": f"timestamp_ausente:{event_ref}", "reason": "Evento sem timestamp explícito; ordenação temporal limitada para este item."})
        timeline.append(entry)
    # order: entries with timestamp first (sorted), then without in original order
    with_ts = [e for e in timeline if e.get("timestamp")]
    without_ts = [e for e in timeline if not e.get("timestamp")]
    try:
        with_ts.sort(key=lambda e: e.get("timestamp") or "")
    except Exception:
        pass
    return with_ts + without_ts, gaps


class CorrelationService:
    def __init__(self, validator: SchemaValidator | None = None):
        self.validator = validator or SchemaValidator()

    def correlate(self, scope: dict[str, Any], alerts_or_evidence: list[dict[str, Any]], ctx: RuntimeContext, request_id: str | None = None) -> dict[str, Any]:
        req_id = request_id or f"req-{uuid4()}"
        consulted = [consulted_source("other", {"scope": scope, "items": len(alerts_or_evidence)}, "ok", utc_now_iso())]
        related_ids = [_item_id(a, i) for i, a in enumerate(alerts_or_evidence)]
        trace = make_trace(request_id=req_id, prompt_version=ctx.prompt_version, agent_version=ctx.agent_version)
        timeline, telemetry_gaps = _timeline(alerts_or_evidence, related_ids)
        shared = _shared_strong_anchors(alerts_or_evidence)
        contradictory = _contradiction_present(alerts_or_evidence)

        known = ["escopo_recebido", f"itens_recebidos:{len(alerts_or_evidence)}"]
        missing: list[str] = []
        for g in telemetry_gaps:
            if g["gap"] not in missing:
                missing.append(g["gap"])

        # Grouping (somente quando há âncoras explícitas)
        grouping: dict[str, Any] = {"by_asset": sorted(set(shared.get("asset", []) + shared.get("host", []) + shared.get("hostname", []))), "by_campaign": sorted(set(shared.get("campaign", []) + shared.get("campaign_id", [])))}
        for key in ("ip", "src_ip", "dst_ip", "user", "account", "incident_id", "case_id"):
            if shared.get(key):
                grouping[f"by_{key}"] = shared[key]

        has_strong_link_evidence = any(v for v in shared.values())
        sources_seen = sorted({_extract_source(x) for x in alerts_or_evidence})

        # R4: sem evidência suficiente de ligação, não afirmar correlação causal/provável
        if len(alerts_or_evidence) < 2:
            missing.extend(["multiplos_sinais_relacionados", "evidencia_de_ligacao_entre_eventos"])
            ds = data_sufficiency(False, known=known, missing=sorted(set(missing)), escalation_required=True, escalation_reason="Dados insuficientes para correlação (R4).")
            result = {
                "correlation_id": f"corr-{uuid4()}",
                "scope": scope,
                "related_alerts": related_ids,
                "classification": classification("indeterminado", "Evidências insuficientes para correlação conclusiva no escopo solicitado; sem conclusão causal."),
                "confidence": "low",
                "consulted_sources": consulted,
                "data_sufficiency": ds,
                "hypotheses": hypotheses(
                    primary=hypothesis("Relação não confirmada", "Não há sinais suficientes ou evidência de ligação para confirmar correlação.", False),
                    alternatives=[hypothesis("Falso positivo/coincidência", "Evento pode ser isolado, independente ou benigno.", True)],
                ),
                "escalation": {"required": True, "reason": "Correlação indeterminada por insuficiência de dados (R4)", "missing_evidence": sorted(set(missing))},
                "trace": trace,
                "timeline": timeline,
                "grouping": grouping,
                "telemetry_gaps": telemetry_gaps,
            }
        elif not has_strong_link_evidence or contradictory:
            if contradictory:
                missing.append("resolucao_de_contradicao_entre_sinais")
            if not has_strong_link_evidence:
                missing.append("evidencia_de_ligacao_explicita_entre_alertas")
            reason_parts = []
            if contradictory:
                reason_parts.append("sinais contraditórios impedem conclusão única")
            if not has_strong_link_evidence:
                reason_parts.append("ausência de âncora/evidência explícita de ligação (campos genéricos compartilhados não são evidência)")
            justification = "Correlação indeterminada: " + "; ".join(reason_parts) + "."
            ds = data_sufficiency(False, known=known + ([f"fontes_observadas:{','.join(sources_seen)}"] if sources_seen else []), missing=sorted(set(missing)), escalation_required=True, escalation_reason=justification)
            alts = [hypothesis("Falso positivo/coincidência", "Eventos podem ser independentes, benignos ou sem relação causal apesar de proximidade.", True)]
            if contradictory:
                alts.append(hypothesis("Interpretação alternativa por fonte", "Fontes apresentam avaliações distintas; é necessária validação adicional antes de concluir relação.", False))
            result = {
                "correlation_id": f"corr-{uuid4()}",
                "scope": scope,
                "related_alerts": related_ids,
                "classification": classification("indeterminado", justification),
                "confidence": "low",
                "consulted_sources": consulted,
                "data_sufficiency": ds,
                "hypotheses": hypotheses(
                    primary=hypothesis("Relação não confirmada", "Não há evidência suficiente e consistente para afirmar correlação entre os sinais.", False),
                    alternatives=alts,
                ),
                "escalation": {"required": True, "reason": justification, "missing_evidence": sorted(set(missing))},
                "trace": trace,
                "timeline": timeline,
                "grouping": grouping,
                "telemetry_gaps": telemetry_gaps,
            }
        else:
            # Evidência explícita de ligação (âncoras fortes compartilhadas), sem contradição detectada
            anchor_desc = ", ".join([f"{k}={','.join(v)}" for k, v in sorted(shared.items()) if v])
            if telemetry_gaps:
                missing.extend([g["gap"] for g in telemetry_gaps])
            ds = data_sufficiency(True, known=known + ["evidencia_de_ligacao_explicita", anchor_desc], missing=sorted(set(missing)), escalation_required=False)
            result = {
                "correlation_id": f"corr-{uuid4()}",
                "scope": scope,
                "related_alerts": related_ids,
                "classification": classification("correlacao_possivel", f"Múltiplos sinais compartilham âncora(s) explícita(s) ({anchor_desc}) no escopo solicitado; relação provável, sujeita a revisão humana."),
                "confidence": "medium",
                "consulted_sources": consulted,
                "data_sufficiency": ds,
                "hypotheses": hypotheses(
                    primary=hypothesis("Incidente/campanha possivelmente relacionado", f"Sinais apresentam ligação explícita por âncora(s): {anchor_desc}.", False),
                    alternatives=[hypothesis("Falso positivo/coincidência", "Apesar da âncora comum, os eventos podem ser independentes ou benignos; validação adicional recomendada.", True)],
                ),
                "trace": trace,
                "timeline": timeline,
                "grouping": grouping,
                "telemetry_gaps": telemetry_gaps,
            }

        validate_correlation_result(result)
        self.validator.validate("correlation-result.schema.json", result)
        emit_audit(
            ctx,
            "correlation_completed",
            {"scope": scope, "count": len(alerts_or_evidence)},
            result["classification"]["justification"],
            {"correlation_id": result["correlation_id"]},
            consulted_sources=consulted,
            confidence=result.get("confidence"),
            correlation_refs=related_ids,
            trace=trace,
        )
        return result

