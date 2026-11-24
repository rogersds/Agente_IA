from __future__ import annotations

import argparse
import json
from pathlib import Path

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.audit_sink.persistent_append_only import PersistentAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.adapters.proposal_queue.persistent_queue import PersistentActionProposalQueue
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.application.query_proposal_service import QueryProposalService


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
    p = argparse.ArgumentParser(description="SOC Agent - query proposal (artifact only, no execution)")
    p.add_argument("--input", required=True, help="JSON file with {objective, ...params}")
    p.add_argument("--audit-log", default="artifacts/audit/events.jsonl")
    p.add_argument("--queue", default="artifacts/proposals/queue.jsonl")
    p.add_argument("--persistent", action="store_true", help="Usa adapters persistentes append-only (fsync) para auditoria/fila, mantendo a mesma interface e sem execução automática")
    args = p.parse_args(argv)
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    queue = PersistentActionProposalQueue(args.queue) if args.persistent else LocalActionProposalQueue(args.queue)
    audit_sink = PersistentAppendOnlyAuditSink(args.audit_log) if args.persistent else LocalAppendOnlyAuditSink(args.audit_log)
    service = QueryProposalService(OpaPolicyEngineAdapter(), queue)
    ctx = RuntimeContext(audit_sink=audit_sink)
    result = service.propose(payload.get("objective", ""), payload, ctx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
