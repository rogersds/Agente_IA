import json
import re
from pathlib import Path

from soc_agent.application.approval_service import ApprovalService
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.contracts_runtime.validator import SchemaValidator


REPO = Path(__file__).resolve().parents[2]


class _QueueSpy:
    def __init__(self):
        self.calls = []
        self.records = {}

    def enqueue(self, proposal):
        self.calls.append(("enqueue", proposal))
        pid = proposal.get("proposal_id") or proposal.get("query_proposal_id")
        self.records[pid] = dict(proposal)
        return {"status": "ok", "operation": "enqueue", "proposal_id": pid, "proposal": self.records[pid]}

    def update_status(self, request):
        self.calls.append(("update_status", request))
        pid = request.get("proposal_id")
        rec = dict(self.records.get(pid, {"proposal_id": pid}))
        rec.update({k: v for k, v in request.items() if k != "status_update"})
        self.records[pid] = rec
        return {"status": "ok", "operation": "update_status", "proposal_id": pid, "proposal": rec}

    def get(self, proposal_id):
        self.calls.append(("get", proposal_id))
        return {"status": "ok", "proposal": self.records.get(proposal_id)}


def test_approval_service_records_state_only_and_never_executes():
    q = _QueueSpy()
    sink = LocalAppendOnlyAuditSink(REPO / "artifacts" / "audit" / "tmp-should-not-be-used.jsonl") if False else LocalAppendOnlyAuditSink  # guard: not used
    # use temp-like in-memory path by tmp_path pattern: create via real LocalAppendOnlyAuditSink on a file under tests context
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        audit = LocalAppendOnlyAuditSink(os.path.join(d, "audit.jsonl"))
        ctx = RuntimeContext(audit_sink=audit)
        svc = ApprovalService(q, SchemaValidator())
        record = {
            "approval_id": "appr-synth-1",
            "proposal_id": "prop-synth-1",
            "proposal_type": "containment",
            "approver": {"id": "SYNTH-APPROVER", "display_name": "SYNTH APPROVER"},
            "decision": "approved",
            "scope": {"target": "prop-synth-1"},
            "decided_at": "2026-01-01T00:00:00Z",
            "justification": "SYNTH",
        }
        res = svc.record_decision(record, ctx)
        assert res["status"] == "recorded"
        ops = [c[0] for c in q.calls]
        assert "enqueue" not in ops
        assert ops.count("update_status") == 1
        # no execution-like operations/method names invoked
        forbidden = {"execute", "run_query", "execute_query", "dispatch", "isolate", "contain", "perform"}
        for name, payload in q.calls:
            blob = json.dumps({"name": name, "payload": payload}, ensure_ascii=False).lower()
            assert not any(f in name.lower() for f in forbidden)
            assert "execution_started" not in blob
        events = audit.read_all()
        assert any(e.get("event_type") == "approval_recorded" for e in events)
        blob_audit = json.dumps(events, ensure_ascii=False).lower()
        assert "execution_started" not in blob_audit


def test_agent_source_has_no_automatic_execution_connectors_or_calls():
    """Varredura estática: código do agente não deve conter caminhos de execução real de consulta/contenção.

    Permitido: avaliação de política local via OPA CLI (subprocess em policy_engine adapter) e utilitários
    de validação; proibido: clientes HTTP/remotos de execução, drivers de contenção/consulta real, etc.
    """
    roots = [
        REPO / "src/soc_agent/application",
        REPO / "src/soc_agent/cli",
        REPO / "src/soc_agent/adapters/alert_source",
        REPO / "src/soc_agent/adapters/search_backend",
        REPO / "src/soc_agent/adapters/enrichment",
        REPO / "src/soc_agent/adapters/threat_intel",
        REPO / "src/soc_agent/adapters/proposal_queue",
        REPO / "src/soc_agent/adapters/audit_sink",
    ]
    forbidden_patterns = [
        r"\bimport\s+requests\b",
        r"\bfrom\s+requests\b",
        r"\bimport\s+httpx\b",
        r"\bfrom\s+httpx\b",
        r"\bimport\s+paramiko\b",
        r"\bimport\s+winrm\b",
        r"\bimport\s+socket\b",  # execução/conexão direta não esperada nesses módulos
        r"\.execute_query\(",
        r"\.run_query\(",
        r"execute_containment\(",
        r"isolate_host\(",
        r"disable_account\(",
        r"block_ip\(",
    ]
    offenders = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.py"):
            text = p.read_text(encoding="utf-8", errors="ignore")
            for pat in forbidden_patterns:
                if re.search(pat, text):
                    offenders.append(f"{p.relative_to(REPO)} matches {pat}")
    assert offenders == [], "Possíveis caminhos de execução/conexão automática encontrados:\n" + "\n".join(offenders)
