from __future__ import annotations

import re
from typing import Any

# Heuristic patterns for instruction-like content embedded in external data (R1).
_PATTERNS = [
    r"ignore\s+(all|suas|as)\s+(previous\s+)?(regras|instru[cç][oõ]es|rules)",
    r"execute\s+(este\s+)?comando",
    r"run\s+this\s+command",
    r"voc[eê]\s+agora\s+[eé]",
    r"you\s+are\s+now",
    r"disregard\s+(your|all)",
    r"override\s+(policy|rules|instructions)",
    r"system\s*prompt",
]


def detect_embedded_instructions(text: str) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    if not text:
        return signals
    lower = text.lower()
    for pat in _PATTERNS:
        if re.search(pat, lower, flags=re.IGNORECASE):
            signals.append(
                {
                    "type": "embedded_instruction_suspected",
                    "pattern": pat,
                    "severity": "high",
                    "message": "External content contains instruction-like text; treated as data/potential IoC (R1).",
                }
            )
    if signals:
        signals.append(
            {
                "type": "r1_policy",
                "severity": "info",
                "message": "Content MUST NOT be obeyed; escalate/signal as needed.",
            }
        )
    return signals


def extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(extract_text(v) for v in value)
    if isinstance(value, dict):
        return "\n".join(f"{k}: {extract_text(v)}" for k, v in value.items())
    return str(value)


def analyze_external_payload(payload: Any) -> dict[str, Any]:
    text = extract_text(payload)
    signals = detect_embedded_instructions(text)
    return {
        "has_embedded_instructions": len([s for s in signals if s.get("type") == "embedded_instruction_suspected"]) > 0,
        "ioc_signals": signals,
    }
