from __future__ import annotations

import argparse
import json
from pathlib import Path

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.application.correlation_service import CorrelationService
from soc_agent.application.orchestrator import RuntimeContext


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SOC Agent - correlation (read-only)")
    p.add_argument("--input", required=True, help="JSON file with {scope, items}")
    p.add_argument("--audit-log", default="artifacts/audit/events.jsonl")
    args = p.parse_args(argv)
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    service = CorrelationService()
    ctx = RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(args.audit_log))
    result = service.correlate(payload.get("scope", {}), payload.get("items", []), ctx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
