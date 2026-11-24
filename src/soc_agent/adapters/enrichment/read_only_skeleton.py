from __future__ import annotations

"""Skeleton de conector read-only para EnrichmentProvider (preparação, sem conexão real)."""

from dataclasses import dataclass
from typing import Any

from soc_agent.domain.common import utc_now_iso


@dataclass
class ReadOnlyConnectorConfig:
    timeout_seconds: float = 5.0
    max_retries: int = 2
    enabled: bool = False


class ReadOnlyEnrichmentSkeleton:
    source_name = "enrichment_skeleton"

    def __init__(self, config: ReadOnlyConnectorConfig | None = None):
        self.config = config or ReadOnlyConnectorConfig()

    def enrich(self, request: dict[str, Any]) -> dict[str, Any]:
        req = request or {}
        safe_ref = {"keys": sorted(list(req.keys()))[:20], "indicator_types_present": isinstance(req.get("indicators"), list)}
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
            "enrichment": None,
        }
