from __future__ import annotations

"""T053/B.C: R3 - saídas, logs/artefatos gerados não expõem credenciais/tokens/chaves/segredos.

Usa apenas sentinelas sintéticas (jamais valores reais). Cobre serializações/resultados de triagem,
correlação, propostas, fila e auditoria gerados pelos fluxos do piloto.
"""

import json
import os
from pathlib import Path

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.containment_proposal_service import ContainmentProposalService
from soc_agent.application.correlation_service import CorrelationService
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.application.query_proposal_service import QueryProposalService
from soc_agent.application.triage_service import TriageService
from soc_agent.domain.common import data_sufficiency


SENTINELS = [
    "SYNTH-SECRET-TOKEN-NOLEAK-001",
    "SYNTH-SECRET-PASSWORD-NOLEAK-001",
    "SYNTH-SECRET-APIKEY-NOLEAK-001",
]


def _dump(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, default=str)


def _assert_no_sentinels_in_payload(payload, where: str):
    text = _dump(payload)
    for s in SENTINELS:
        assert s not in text, f"sentinela de segredo vazou em {where}"


def _ctx(tmp_path):
    return RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))


def test_r3_outputs_artifacts_queue_audit_do_not_leak_synthetic_secrets(tmp_path, monkeypatch):
    # Sentinelas em env vars de nomes sensíveis NÃO devem ser copiadas para artefatos por padrão
    monkeypatch.setenv("SYNTH_SECRET_TOKEN", SENTINELS[0])
    monkeypatch.setenv("SYNTH_API_KEY", SENTINELS[2])

    audit_sink = LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl")
    ctx = RuntimeContext(audit_sink=audit_sink)
    queue_q = LocalActionProposalQueue(tmp_path / "q_queue.jsonl")
    queue_c = LocalActionProposalQueue(tmp_path / "c_queue.jsonl")

    # Triagem
    alert = {
        "alert_id": "SYNTH-ALERT-R3",
        "source": "SYNTH-SRC",
        "severity": "medium",
        "timestamp": "2026-01-01T00:00:00Z",
        "content": {"message": "SYNTH-MSG", "host": "SYNTH-HOST"},
    }
    triage = TriageService().triage_alert(alert, ctx)
    _assert_no_sentinels_in_payload(triage, "triage_result")

    # Correlação
    scope = {"requested_by": "SYNTH", "period": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"}, "assets": ["SYNTH-HOST"]}
    items = [
        {"alert_id": "SYNTH-A1", "timestamp": "2026-01-01T00:10:00Z", "asset": "SYNTH-HOST", "source": "SYNTH-SRC"},
        {"alert_id": "SYNTH-A2", "timestamp": "2026-01-01T00:11:00Z", "asset": "SYNTH-HOST", "source": "SYNTH-SRC"},
    ]
    corr = CorrelationService().correlate(scope, items, ctx, request_id="SYNTH-REQ-R3")
    _assert_no_sentinels_in_payload(corr, "correlation_result")

    # Proposta de consulta
    qp = QueryProposalService(OpaPolicyEngineAdapter(), queue_q).propose(
        "SYNTH-OBJ",
        {
            "time_window": {"start": "2026-01-01T00:00:00Z", "end": "2026-01-01T01:00:00Z"},
            "data_scope": {"index": "SYNTH-IDX"},
            "cost_estimate": {"summary": "SYNTH", "estimated_scan_units": 1},
            "query_artifact": {"text": "SYNTH-QUERY", "language": "kql", "version": "v1"},
        },
        ctx,
    )
    _assert_no_sentinels_in_payload(qp, "query_proposal")

    # Proposta de contenção
    cp = ContainmentProposalService(OpaPolicyEngineAdapter(), queue_c).propose(
        "SYNTH-INC",
        {
            "action_category": "host",
            "target": {"identifier": "SYNTH-HOST", "type": "host", "unambiguous": True},
            "rollback_plan": {"summary": "S", "steps": ["s"], "responsible": "r", "validation": "v", "limitations": []},
            "data_sufficiency": data_sufficiency(True, ["k"], [], False),
        },
        ctx,
    )
    _assert_no_sentinels_in_payload(cp, "containment_proposal")

    # Filas e auditoria persistidos
    for p in [tmp_path / "q_queue.jsonl", tmp_path / "c_queue.jsonl", tmp_path / "audit.jsonl"]:
        if p.exists():
            text = p.read_text(encoding="utf-8")
            for s in SENTINELS:
                assert s not in text, f"sentinela de segredo vazou em artefato {p.name}"

    events = audit_sink.read_all()
    _assert_no_sentinels_in_payload(events, "audit_events")
    _assert_no_sentinels_in_payload(queue_q.get(qp["query_proposal_id"]), "queue_query_record")
    _assert_no_sentinels_in_payload(queue_c.get(cp["proposal_id"]), "queue_containment_record")
