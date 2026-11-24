from __future__ import annotations

from soc_agent.contracts_runtime.validator import SchemaValidator
from soc_agent.domain.common import classification, consulted_source, data_sufficiency, hypotheses, hypothesis, make_trace, utc_now_iso


def _valid_correlation_result() -> dict:
    trace = make_trace(request_id="SYNTH-REQ-CORR-001", agent_version="0.1.0")
    return {
        "correlation_id": "SYNTH-CORR-001",
        "scope": {
            "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
            "assets": ["SYNTH-HOST-01"],
            "requested_by": "SYNTH-ANALYST-01",
        },
        "related_alerts": ["SYNTH-ALERT-001", "SYNTH-ALERT-002"],
        "classification": classification("correlacao_possivel", "Sinais no mesmo ativo e janela temporal indicam relação provável, sujeita a revisão."),
        "confidence": "medium",
        "consulted_sources": [
            consulted_source("alert_source", {"alert_id": "SYNTH-ALERT-001"}, "ok", "2026-01-01T00:05:00Z", source_id="SYNTH-SRC-ALERTS"),
            consulted_source("alert_source", {"alert_id": "SYNTH-ALERT-002"}, "ok", "2026-01-01T00:06:00Z", source_id="SYNTH-SRC-ALERTS"),
        ],
        "data_sufficiency": data_sufficiency(True, known=["escopo_recebido", "dois_alertas_no_mesmo_host"], missing=[]),
        "hypotheses": hypotheses(
            primary=hypothesis("Atividade relacionada no mesmo ativo", "Alertas compartilham SYNTH-HOST-01 na janela solicitada.", False),
            alternatives=[hypothesis("Coincidência/falso positivo", "Eventos podem ser independentes apesar de ativo comum.", True)],
        ),
        "trace": trace,
        "timeline": [
            {"timestamp": "2026-01-01T00:05:00Z", "event_ref": "SYNTH-ALERT-001", "source": "SYNTH-SRC-ALERTS", "description": "SYNTH-EVENT-A"},
            {"timestamp": "2026-01-01T00:06:00Z", "event_ref": "SYNTH-ALERT-002", "source": "SYNTH-SRC-ALERTS", "description": "SYNTH-EVENT-B"},
        ],
        "grouping": {"by_asset": ["SYNTH-HOST-01"], "by_campaign": []},
        "telemetry_gaps": [],
    }


def test_correlation_result_conforms_to_contract_schemas():
    """T031: contrato de correlação conforme correlation-result + common schemas."""
    validator = SchemaValidator()
    validator.validate("correlation-result.schema.json", _valid_correlation_result())


def test_correlation_result_indeterminate_with_explicit_gaps_and_escalation():
    """T031: cenário indeterminado (R4) com lacunas/suficiência e escalonamento representáveis no contrato."""
    validator = SchemaValidator()
    trace = make_trace(request_id="SYNTH-REQ-CORR-002")
    result = {
        "correlation_id": "SYNTH-CORR-002",
        "scope": {"period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}, "assets": ["SYNTH-HOST-01"]},
        "related_alerts": ["SYNTH-ALERT-010"],
        "classification": classification("indeterminado", "Sinais insuficientes para confirmar relação causal no escopo."),
        "confidence": "low",
        "consulted_sources": [
            consulted_source("alert_source", {"scope": "SYNTH-SCOPE"}, "partial", "2026-01-01T00:10:00Z", source_id="SYNTH-SRC-ALERTS"),
        ],
        "data_sufficiency": data_sufficiency(
            False,
            known=["alerta_unico_recebido"],
            missing=["telemetria_host_complementar", "evidencia_de_ligacao_entre_eventos"],
            escalation_required=True,
            escalation_reason="Correlação indeterminada por insuficiência de dados.",
        ),
        "hypotheses": hypotheses(
            primary=hypothesis("Relação não confirmada", "Não há evidência suficiente para afirmar correlação.", False),
            alternatives=[hypothesis("Falso positivo/coincidência", "Evento pode ser isolado ou benigno.", True)],
        ),
        "escalation": {"required": True, "reason": "Correlação indeterminada (R4)", "missing_evidence": ["telemetria_host_complementar"]},
        "trace": trace,
        "timeline": [
            {"timestamp": "2026-01-01T00:10:00Z", "event_ref": "SYNTH-ALERT-010", "source": "SYNTH-SRC-ALERTS", "description": "SYNTH-EVENT-ISOLADO"},
        ],
        "telemetry_gaps": [
            {"gap": "telemetria_host_complementar", "reason": "Fonte de telemetria do host não disponível no escopo consultado"},
        ],
    }
    validator.validate("correlation-result.schema.json", result)


def test_correlation_result_with_optional_fields_absent_still_conforms():
    """T031/B.3: campos opcionais ausentes (ex.: escalation, source_id, details, trace versions) permanecem válidos."""
    validator = SchemaValidator()
    trace = {"request_id": "SYNTH-REQ-CORR-003", "created_at": utc_now_iso()}
    result = {
        "correlation_id": "SYNTH-CORR-003",
        "scope": {"period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}},
        "related_alerts": ["SYNTH-ALERT-020", "SYNTH-ALERT-021"],
        "classification": {"label": "indeterminado", "justification": "Sem evidência suficiente de ligação."},
        "confidence": "unknown",
        "consulted_sources": [
            {"capability": "alert_source", "reference": {"ids": ["SYNTH-ALERT-020", "SYNTH-ALERT-021"]}, "status": "ok", "consulted_at": "2026-01-01T00:20:00Z"}
        ],
        "data_sufficiency": {"sufficient": False, "known": ["alertas_recebidos"], "missing": ["evidencia_de_ligacao"], "escalation_required": True},
        "hypotheses": {
            "primary": {"title": "Relação não confirmada", "rationale": "Ausência de âncora comum comprovada."},
            "alternatives": [{"title": "Eventos independentes", "rationale": "Podem não ter relação causal.", "is_false_positive": True}],
        },
        "trace": trace,
    }
    validator.validate("correlation-result.schema.json", result)
