from __future__ import annotations

import argparse
import json
from pathlib import Path

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.application.query_proposal_service import QueryProposalService


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="SOC Agent - query proposal (artifact only, no execution)")
    p.add_argument("--input", required=True, help="JSON file with {objective, ...params}")
    p.add_argument("--audit-log", default="artifacts/audit/events.jsonl")
    p.add_argument("--queue", default="artifacts/proposals/queue.jsonl")
    args = p.parse_args(argv)
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    service = QueryProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(args.queue))
    ctx = RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(args.audit_log))
    result = service.propose(payload.get("objective", ""), payload, ctx)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
