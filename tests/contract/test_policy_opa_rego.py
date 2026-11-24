from __future__ import annotations

from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.domain.policy import build_policy_request

from tests.contract.opa_test_support import require_opa_or_fail_or_skip


def test_opa_denies_containment_without_rollback():
    require_opa_or_fail_or_skip()
    adapter = OpaPolicyEngineAdapter()
    req = build_policy_request(
        request_id="r1",
        proposal_kind="containment",
        candidate={
            "classification": {"label": "proposta"},
            "hypotheses": {"alternatives": [{"text": "fp", "is_false_positive": True}]},
            "consulted_sources": [{"capability": "alert_source", "reference": {}, "status": "ok", "consulted_at": "2026-01-01T00:00:00Z"}],
            "trace": {"request_id": "r1"},
        },
        context={
            "target_ambiguous": False,
            "data_sufficient": True,
            "rollback_documented": False,
            "has_explicit_approval_record": False,
            "has_false_positive_alternative": True,
        },
    )
    decision = adapter.evaluate(req)
    assert decision["result"] in {"deny", "block_and_escalate"}
    assert decision["policy_version"]


def test_policy_adapter_fail_closed_without_opa(tmp_path, monkeypatch):
    # force adapter to miss opa/policy -> fail-closed
    adapter = OpaPolicyEngineAdapter(policy_path=tmp_path / "missing.rego")
    req = build_policy_request("r1", "query_proposal", {}, {"query_parameters_complete": False})
    decision = adapter.evaluate(req)
    assert decision["result"] == "block_and_escalate"
    assert decision["decision_id"]
    assert decision["policy_id"]
    assert isinstance(decision["reasons"], list) and len(decision["reasons"]) >= 1
