from __future__ import annotations

"""Skeleton de conector read-only para SearchBackend (preparação, sem conexão real).

Consultas reais permanecem como propostas versionáveis (janela/escopo/custo) e execução
externa exige aprovação humana registrada (R7/R2). Fail-safe: não executa busca real.
"""

from dataclasses import dataclass
from typing import Any

from soc_agent.domain.common import utc_now_iso


@dataclass
class ReadOnlyConnectorConfig:
    timeout_seconds: float = 5.0
    max_retries: int = 2
    enabled: bool = False


class ReadOnlySearchBackendSkeleton:
    source_name = "search_backend_skeleton"

    def __init__(self, config: ReadOnlyConnectorConfig | None = None):
        self.config = config or ReadOnlyConnectorConfig()

    def search(self, request: dict[str, Any]) -> dict[str, Any]:
        req = request or {}
        safe_ref = {
            "keys": sorted(list(req.keys()))[:20],
            "has_time_window": "time_window" in req,
            "has_data_scope": "data_scope" in req,
            "has_cost_estimate": "cost_estimate" in req,
        }
        return {
            "status": "unavailable",
            "read_only": True,
            "connected": False,
            "execution_performed": False,
            "source": self.source_name,
            "reason": "connector_not_configured_or_not_authorized",
            "request_ref": safe_ref,
            "timeout_seconds": self.config.timeout_seconds,
            "max_retries": self.config.max_retries,
            "timestamp": utc_now_iso(),
            "note": "Consulta real não executada; requer proposta aprovada e executor externo autorizado.",
        }
