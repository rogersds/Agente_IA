from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from soc_agent.adapters.audit_sink.local_append_only import LocalAppendOnlyAuditSink
from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.adapters.proposal_queue.local_queue import LocalActionProposalQueue
from soc_agent.application.containment_proposal_service import ContainmentProposalService
from soc_agent.application.orchestrator import RuntimeContext
from soc_agent.contracts_runtime.validator import SchemaValidationError, SchemaValidator
from soc_agent.domain.common import data_sufficiency

SENTINELS = [
    "SYNTH_SECRET_VALUE_DO_NOT_LEAK",
    "SYNTH_TOKEN_12345",
    "SYNTH_PASSWORD_ABC",
]


def _ctx(tmp_path):
    return RuntimeContext(audit_sink=LocalAppendOnlyAuditSink(tmp_path / "audit.jsonl"))


def _ambiguous_payload():
    return {
        "incident_or_alert_ref": "SYNTH-INC-CT03",
        "action_category": "host",
        "target": {"ambiguous": True},
        "rollback_plan": {"summary": "S", "steps": ["s"], "responsible": "r", "validation": "v", "limitations": []},
        "data_sufficiency": data_sufficiency(True, ["k"], [], False),
        "confidence": "low",
    }


def _assert_no_sentinels(obj) -> None:
    blob = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    for s in SENTINELS:
        assert s not in blob


def _assert_no_execution_markers(obj) -> None:
    # Não deve haver indicação de execução; proposta não é criada.
    assert "executed" not in json.dumps(obj, ensure_ascii=False).lower() or obj.get("outcome", {}).get("execution_performed") is False


def test_ct03_service_ambiguous_target_audited_no_queue_no_proposal(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    queue_path = tmp_path / "queue.jsonl"
    service = ContainmentProposalService(OpaPolicyEngineAdapter(), LocalActionProposalQueue(queue_path))
    ctx = _ctx(tmp_path)

    from soc_agent.domain.containment import ContainmentAmbiguousTargetBlockedError

    with pytest.raises(ContainmentAmbiguousTargetBlockedError) as ei:
        service.propose("SYNTH-INC-CT03", _ambiguous_payload(), ctx, request_id="SYNTH-REQ-CT03")

    assert ei.value.request_id == "SYNTH-REQ-CT03"
    assert ei.value.audit_id

    events = ctx.audit_sink.read_all()
    blocked = [e for e in events if e.get("event_type") == "containment_proposal_blocked_ambiguous_target"]
    assert len(blocked) == 1
    ev = blocked[0]
    SchemaValidator().validate("audit-event.schema.json", ev)
    assert ev.get("trace", {}).get("request_id") == "SYNTH-REQ-CT03"
    assert ev.get("outcome", {}).get("blocked") is True
    assert ev.get("outcome", {}).get("proposal_created") is False
    assert ev.get("outcome", {}).get("proposal_enqueued") is False
    assert ev.get("outcome", {}).get("execution_performed") is False
    assert ev.get("input_summary", {}).get("incident_or_alert_ref") == "SYNTH-INC-CT03"
    assert ev.get("input_summary", {}).get("block_reason") == "ambiguous_target"

    # (iii) fila sem nenhum item para o caso; nenhum arquivo de proposta criado
    assert (not queue_path.exists()) or queue_path.read_text(encoding="utf-8").strip() == ""
    # (iv) nenhuma execução / sem proposta
    assert "proposal_id" not in json.dumps(ev.get("outcome", {}), ensure_ascii=False)
    _assert_no_execution_markers(ev)
    # (v) sentinelas R3 ausentes
    _assert_no_sentinels(ev)


def test_ct03_cli_ambiguous_target_controlled_exit_stderr_audit_no_queue(tmp_path):
    inp = tmp_path / "ct03.json"
    inp.write_text(json.dumps(_ambiguous_payload(), ensure_ascii=False), encoding="utf-8")
    audit = tmp_path / "audit.jsonl"
    queue = tmp_path / "queue.jsonl"
    cmd = [
        sys.executable,
        "-m",
        "soc_agent.cli.propose_containment",
        "--input",
        str(inp),
        "--audit-log",
        str(audit),
        "--queue",
        str(queue),
    ]
    import os
    env = os.environ.copy()
    src = str((Path(__file__).resolve().parents[2] / "src"))
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
    # (i) estado seguro, sem traceback, exit code não-zero documentado e distinto de erro inesperado
    assert proc.returncode == 10
    assert "Traceback" not in (proc.stderr or "")
    assert "Traceback" not in (proc.stdout or "")
    assert "ambíguo" in (proc.stderr or "").lower() or "ambiguo" in (proc.stderr or "").lower()
    assert (proc.stdout or "").strip() == ""

    events = [json.loads(l) for l in audit.read_text(encoding="utf-8").splitlines() if l.strip()]
    blocked = [e for e in events if e.get("event_type") == "containment_proposal_blocked_ambiguous_target"]
    assert len(blocked) == 1
    SchemaValidator().validate("audit-event.schema.json", blocked[0])
    assert (not queue.exists()) or queue.read_text(encoding="utf-8").strip() == ""
    _assert_no_sentinels(blocked[0])


def test_ct03_non_ambiguous_schema_failure_still_propagates(tmp_path):
    """(vi) Falha de schema NÃO relacionada a ambiguidade continua propagando como erro."""

    class FailOnContainmentSchemaValidator(SchemaValidator):
        def validate(self, schema_name: str, data):  # type: ignore[override]
            if schema_name == "containment-proposal.schema.json":
                raise SchemaValidationError("SYNTH_FORCED_SCHEMA_ERROR: $.forced: invalid")
            return super().validate(schema_name, data)

    service = ContainmentProposalService(
        OpaPolicyEngineAdapter(),
        LocalActionProposalQueue(tmp_path / "q.jsonl"),
        validator=FailOnContainmentSchemaValidator(),
    )
    ctx = _ctx(tmp_path)
    payload = {
        "incident_or_alert_ref": "SYNTH-INC-NONAMB",
        "action_category": "host",
        "target": {"identifier": "SYNTH-HOST-OK", "type": "host", "unambiguous": True},
        "rollback_plan": {"summary": "S", "preconditions": ["p"], "steps": ["s"], "responsible": "r", "validation": "v", "limitations": []},
        "data_sufficiency": data_sufficiency(True, ["k"], [], False),
        "confidence": "low",
    }
    with pytest.raises(SchemaValidationError) as ei:
        service.propose("SYNTH-INC-NONAMB", payload, ctx, request_id="SYNTH-REQ-NONAMB")
    assert "SYNTH_FORCED_SCHEMA_ERROR" in str(ei.value)
    # Não deve ter gerado evento de bloqueio por ambiguidade
    events = ctx.audit_sink.read_all()
    assert not any(e.get("event_type") == "containment_proposal_blocked_ambiguous_target" for e in events)
    # Nenhum item enfileirado (falha antes do enqueue no fluxo normal)
    qpath = tmp_path / "q.jsonl"
    assert (not qpath.exists()) or qpath.read_text(encoding="utf-8").strip() == ""
