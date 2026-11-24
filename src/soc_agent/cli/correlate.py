from __future__ import annotations

import argparse
import json
from pathlib import Path

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.audit_sink.persistent_append_only import PersistentAppendOnlyAuditSink
from soc_agent.application.correlation_service import CorrelationService
from soc_agent.application.orchestrator import RuntimeContext


def _configure_stdio_utf8() -> None:
    import sys
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    p = argparse.ArgumentParser(description="SOC Agent - correlação (read-only)")
    p.add_argument("--input", required=True, help="JSON file with {scope, items}")
    p.add_argument("--audit-log", default="artifacts/audit/events.jsonl")
    p.add_argument("--persistent", action="store_true", help="Usa adapter persistente append-only (fsync) para auditoria, mantendo a mesma interface e sem execução automática")
    args = p.parse_args(argv)
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    service = CorrelationService()
    audit_sink = PersistentAppendOnlyAuditSink(args.audit_log) if args.persistent else LocalAppendOnlyAuditSink(args.audit_log)
    ctx = RuntimeContext(audit_sink=audit_sink)
    result = service.correlate(payload.get("scope", {}), payload.get("items", []), ctx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
