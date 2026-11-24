from __future__ import annotations

import argparse
import json
from pathlib import Path

from soc_agent.adapters.alert_source.local_source import LocalAlertSourceAdapter
from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.enrichment.local_enrichment import LocalEnrichmentAdapter
from soc_agent.adapters.llm_provider.adapter import LocalDeterministicLlmProvider
from soc_agent.adapters.search_backend.local_search import LocalSearchBackendAdapter
from soc_agent.adapters.threat_intel.local_intel import LocalThreatIntelAdapter
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.application.triage_service import TriageService


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SOC Agent - triage (read-only)")
    p.add_argument("--alert-file", help="Path to alert JSON file")
    p.add_argument("--alert-id", help="Alert id to load from local source")
    p.add_argument("--audit-log", default="artifacts/audit/events.jsonl")
    args = p.parse_args(argv)

    if args.alert_file:
        alert = json.loads(Path(args.alert_file).read_text(encoding="utf-8"))
    elif args.alert_id:
        alert = LocalAlertSourceAdapter().get_alert(args.alert_id)
        if alert is None:
            raise SystemExit(f"Alert not found: {args.alert_id}")
    else:
        raise SystemExit("Provide --alert-file or --alert-id")

    service = TriageService(
        alert_source=LocalAlertSourceAdapter(),
        search_backend=LocalSearchBackendAdapter(),
        enrichment=LocalEnrichmentAdapter(),
        threat_intel=LocalThreatIntelAdapter(),
        llm_provider=LocalDeterministicLlmProvider(),
    )
    ctx = RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(args.audit_log))
    result = service.triage_alert(alert, ctx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
