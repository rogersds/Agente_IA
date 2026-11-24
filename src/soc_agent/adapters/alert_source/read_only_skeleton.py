from __future__ import annotations

"""Skeleton de conector read-only para AlertSource (preparação, sem conexão real).

- Read-only por padrão; não executa ações destrutivas.
- Timeout e retries limitados configuráveis; fail-safe (não conecta a sistemas reais).
- Não registra/imprime segredos; entradas tratadas como dado (R1/R3).
"""

from dataclasses import dataclass
from typing import Any

from soc_agent.domain.common import utc_now_iso


@dataclass
class ReadOnlyConnectorConfig:
    timeout_seconds: float = 5.0
    max_retries: int = 2
    enabled: bool = False  # permanece desabilitado até configuração/aprovação humana em ambiente autorizado


class ReadOnlyAlertSourceSkeleton:
    """Implementa a interface operacional de AlertSource de forma fail-safe."""

    source_name = "alert_source_skeleton"

    def __init__(self, config: ReadOnlyConnectorConfig | None = None):
        self.config = config or ReadOnlyConnectorConfig()

    def _fail_safe(self, operation: str, request: dict[str, Any]) -> dict[str, Any]:
        # Nunca conecta; retorna indisponibilidade controlada sem vazar payload sensível.
        safe_ref = {"operation": operation, "keys": sorted(list(request.keys()))[:20]}
        return {
            "status": "unavailable",
            "read_only": True,
            "connected": False,
            "source": self.source_name,
            "reason": "connector_not_configured_or_not_authorized",
            "request_ref": safe_ref,
            "timeout_seconds": self.config.timeout_seconds,
            "max_retries": self.config.max_retries,
            "timestamp": utc_now_iso(),
        }

    def fetch_alerts(self, request: dict[str, Any]) -> dict[str, Any]:
        return self._fail_safe("fetch_alerts", request or {})

    def get_alert(self, request: dict[str, Any]) -> dict[str, Any]:
        return self._fail_safe("get_alert", request or {})
