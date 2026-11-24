import json
import os
from pathlib import Path

from soc_agent.adapters.audit_sink.persistent_append_only import PersistentAppendOnlyAuditSink
from soc_agent.adapters.proposal_queue.persistent_queue import PersistentActionProposalQueue


def _ensure_opa_env(monkeypatch):
    # Usa apenas nomes de variáveis de ambiente; resolve caminho local conhecido se necessário para execução do teste.
    if os.environ.get("OPA_BIN"):
        return
    known = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages/open-policy-agent.opa_Microsoft.Winget.Source_8wekyb3d8bbwe/opa.exe"
    if known.exists():
        monkeypatch.setenv("PATH", str(known.parent) + os.pathsep + os.environ.get("PATH", ""))


def test_persistent_cli_wiring_query_persists_reloads_and_no_execution(tmp_path, monkeypatch, capsys):
    _ensure_opa_env(monkeypatch)
    from soc_agent.cli.propose_query import main as propose_query_main

    inp = tmp_path / "q.json"
    inp.write_text(json.dumps({
        "objective": "SYNTH busca persistente",
        "time_window": {"start": "2026-01-10T00:00:00Z", "end": "2026-01-10T01:00:00Z"},
        "data_scope": {"index": "SYNTH-IDX"},
        "cost_estimate": {"summary": "baixo", "estimated_scan_units": 1},
        "query_artifact": {"language": "kql", "text": "SYNTH_PERSIST_Q", "version": "v1"}
    }, ensure_ascii=False), encoding="utf-8")
    audit = tmp_path / "audit.jsonl"
    queue = tmp_path / "queue.jsonl"

    rc = propose_query_main(["--input", str(inp), "--audit-log", str(audit), "--queue", str(queue), "--persistent"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    assert out["execution_status"] in {"pending_review", "blocked", "proposed"}
    assert out["requires_human_review"] is True

    assert audit.exists() and queue.exists()
    # reload via persistent adapters (mesma interface operacional)
    sink = PersistentAppendOnlyAuditSink(audit)
    q = PersistentActionProposalQueue(queue)
    assert len(sink.read_all()) >= 1
    pid = out["query_proposal_id"]
    got = q.get(pid)
    assert got["status"] == "ok"
    assert got["proposal"]["query_proposal_id"] == pid
    assert got["proposal"]["execution_status"] == out["execution_status"]


def test_persistent_cli_wiring_containment_approval_updates_state_without_execution(tmp_path, monkeypatch, capsys):
    _ensure_opa_env(monkeypatch)
    from soc_agent.cli.propose_containment import main as propose_containment_main

    inp = tmp_path / "c.json"
    inp.write_text(json.dumps({
        "incident_or_alert_ref": "SYNTH-INC-PERSIST",
        "action_category": "host",
        "target": {"identifier": "HOST-P", "type": "host", "unambiguous": True},
        "rollback_plan": {
            "summary": "SYNTH rollback",
            "steps": ["Reverter isolamento"],
            "responsible": "SOC-ONCALL",
            "validation": "Validar conectividade",
            "limitations": []
        },
        "confidence": 0.6,
        "data_sufficiency": {"sufficient": True, "known": ["host"], "missing": [], "escalation_required": False}
    }, ensure_ascii=False), encoding="utf-8")
    audit = tmp_path / "audit.jsonl"
    queue = tmp_path / "queue.jsonl"

    rc = propose_containment_main(["--input", str(inp), "--audit-log", str(audit), "--queue", str(queue), "--persistent"])
    assert rc == 0
    out = json.loads(capsys.readouterr().out)
    pid = out["proposal_id"]
    assert out["approval_status"] in {"pending", "blocked"}
    assert out["approval_requirement"]["execution_permitted"] is False
    assert out["approval_requirement"]["requires_human_approval"] is True

    # Aprovação explícita registrada altera apenas estado na fila; nenhuma execução é disparada.
    q = PersistentActionProposalQueue(queue)
    q.update_status({"proposal_id": pid, "approval_status": "approved", "approval_record": {"decision": "approved", "approver": "SYNTH-REVIEWER", "proposal_id": pid}})
    q2 = PersistentActionProposalQueue(queue)
    got = q2.get(pid)["proposal"]
    assert got.get("approval_status") == "approved" or got.get("approval_record", {}).get("decision") == "approved"
    # artefato continua sendo recomendação/proposta sem permissão de execução automática
    assert out["approval_requirement"]["execution_permitted"] is False
    assert "execution_started" not in json.dumps(got, ensure_ascii=False).lower()
    assert Path(audit).exists() and Path(queue).exists()
