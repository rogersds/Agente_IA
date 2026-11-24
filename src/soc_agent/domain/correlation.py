from __future__ import annotations

from typing import Any

from .validators import validate_classification, validate_data_sufficiency, validate_hypotheses, validate_trace

REQUIRED_FIELDS = [
    "correlation_id",
    "scope",
    "related_alerts",
    "classification",
    "confidence",
    "consulted_sources",
    "data_sufficiency",
    "hypotheses",
    "trace",
]


def validate_correlation_result(result: dict[str, Any]) -> None:
    for f in REQUIRED_FIELDS:
        if f not in result:
            raise ValueError(f"CorrelationResult missing required field: {f}")
    validate_classification(result["classification"])
    validate_data_sufficiency(result["data_sufficiency"])
    validate_hypotheses(result["hypotheses"])
    validate_trace(result["trace"])
    if not isinstance(result.get("related_alerts"), list):
        raise ValueError("CorrelationResult.related_alerts must be a list")
    if not isinstance(result.get("consulted_sources"), list):
        raise ValueError("CorrelationResult.consulted_sources must be a list")
