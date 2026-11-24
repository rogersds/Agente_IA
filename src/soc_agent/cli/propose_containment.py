from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.audit_sink.persistent_append_only import PersistentAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.adapters.proposal_queue.persistent_queue import PersistentActionProposalQueue
from soc_agent.application.containment_proposal_service import ContainmentProposalService
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.domain.containment import ContainmentAmbiguousTargetBlockedError

# Exit code documentado (distinto de erro inesperado/traceback): bloqueio controlado
# por desenho para alvo ambíguo (R2/R4), com auditoria append-only e sem proposta/fila/execução.
EXIT_BLOCKED_AMBIGUOUS_TARGET = 10


def _configure_stdio_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def main(argv: list[str] | None = None) -> int:
    _configure_stdio_utf8()
    p = argparse.ArgumentParser(
        description=(
            "SOC Agent - containment proposal (recommendation only, no execution). "
            f"Exit {EXIT_BLOCKED_AMBIGUOUS_TARGET}: bloqueio controlado por alvo ambíguo (auditado, sem proposta/fila)."
        )
    )
    p.add_argument("--input", required=True, help="JSON file with incident_or_alert_ref and proposal params")
    p.add_argument("--audit-log", default="artifacts/audit/events.jsonl")
    p.add_argument("--queue", default="artifacts/proposals/queue.jsonl")
    p.add_argument("--persistent", action="store_true", help="Usa adapters persistentes append-only (fsync) para auditoria/fila, mantendo a mesma interface e sem execução automática")
    args = p.parse_args(argv)
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    ref = payload.get("incident_or_alert_ref") or payload.get("alert_id") or "unknown"
    queue = PersistentActionProposalQueue(args.queue) if args.persistent else LocalActionProposalQueue(args.queue)
    audit_sink = PersistentAppendOnlyAuditSink(args.audit_log) if args.persistent else LocalAppendOnlyAuditSink(args.audit_log)
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), queue)
    ctx = RuntimeContext(audit_sink=audit_sink)
    try:
        result = service.propose(ref, payload, ctx, approval_record=payload.get("approval_record"))
    except ContainmentAmbiguousTargetBlockedError as e:
        # Mensagem controlada, sem traceback; auditoria já registrada pelo serviço.
        msg = str(e)
        if getattr(e, "audit_id", None):
            msg = f"{msg} audit_id={e.audit_id}"
        print(msg, file=sys.stderr)
        return EXIT_BLOCKED_AMBIGUOUS_TARGET
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
