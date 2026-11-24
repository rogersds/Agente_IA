from __future__ import annotations

from typing import Any

from .common import classification, data_sufficiency, hypotheses, hypothesis, make_trace
from .validators import validate_classification, validate_data_sufficiency, validate_hypotheses, validate_trace


REQUIRED_FIELDS = [
    "triage_id",
    "alert_id",
    "classification",
    "confidence",
    "consulted_sources",
    "data_sufficiency",
    "hypotheses",
    "trace",
]


def validate_triage_result(result: dict[str, Any]) -> None:
    for f in REQUIRED_FIELDS:
        if f not in result:
            raise ValueError(f"TriageResult missing required field: {f}")
    validate_classification(result["classification"])
    validate_data_sufficiency(result["data_sufficiency"])
    validate_hypotheses(result["hypotheses"])
    validate_trace(result["trace"])
    if not isinstance(result.get("consulted_sources"), list):
        raise ValueError("TriageResult.consulted_sources must be a list")
    if result.get("confidence") is None:
        raise ValueError("TriageResult.confidence must be explicit")


def build_indeterminate_triage(
    triage_id: str,
    alert_id: str,
    consulted_sources: list[dict[str, Any]],
    known: list[str],
    missing: list[str],
    reason: str,
    trace: dict[str, Any],
    ioc_signals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    result = {
        "triage_id": triage_id,
        "alert_id": alert_id,
        "classification": classification("indeterminado", reason),
        "confidence": "low",
        "consulted_sources": consulted_sources,
        "data_sufficiency": data_sufficiency(
            sufficient=False,
            known=known,
            missing=missing,
            escalation_required=True,
            escalation_reason=reason,
        ),
        "hypotheses": hypotheses(
            primary=hypothesis("Hipótese principal indeterminada", reason, False),
            alternatives=[
                hypothesis("Falso positivo ou dado benigno", "Evidências insuficientes ou ambíguas podem indicar falso positivo.", True)
            ],
        ),
        "recommended_next_steps": ["Escalar para revisão humana", "Coletar evidências adicionais nas fontes autorizadas"],
        "escalation": {"required": True, "reason": reason},
        "trace": trace,
    }
    if ioc_signals:
        result["ioc_signals"] = ioc_signals
    validate_triage_result(result)
    return result
