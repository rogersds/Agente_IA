from __future__ import annotations

"""
B.0 — Equivalência semântica da política (pré-requisito Fase B).

Prova, com OPA real, que as decisões da política Rego v1 (migração de sintaxe em
specs/001-soc-triage-correlacao/contracts/policy/action_proposal.rego) preservam as
condições semânticas esperadas anteriormente: bloqueio R2/R5, bloqueio/revisão R4/R7 e
permissão de EMISSÃO de proposta (nunca execução) quando válida e completa.

Baseline executado pré-migração não está disponível neste ambiente; estes casos
codificam as expectativas semânticas declaradas pela política/contratos (comportamento
anterior) e devem produzir resultados idênticos. Divergência => falha do teste e deve
ser reportada antes de prosseguir (não ajustar regra/teste para mascarar).

Entradas/saídas usam apenas sentinelas sintéticas (R3).
"""

from soc_agent.adapters.policy_engine.opa_adapter import OpaPolicyEngineAdapter
from soc_agent.domain.policy import build_policy_request

from tests.contract.opa_test_support import require_opa_or_fail_or_skip


def _base_candidate() -> dict:
    # Candidato mínimo sintético; a política opera sobre proposal_kind/context/candidate.
    return {
        "classification": {"label": "proposta"},
        "trace": {"request_id": "SYNTH-TRACE-001"},
        "candidate_id": "SYNTH-CANDIDATE-001",
    }


def test_b0_valid_complete_containment_proposal_allows_emission_not_execution():
    """Proposta válida e completa → emissão PERMITIDA (proposta, nunca execução)."""
    require_opa_or_fail_or_skip()
    adapter = OpaPolicyEngineAdapter()
    req = build_policy_request(
        request_id="SYNTH-REQ-ALLOW-001",
        proposal_kind="containment",
        candidate={
            **_base_candidate(),
            "execution_requested": False,
            "hypotheses": {"alternatives": [{"text": "SYNTH-FP", "is_false_positive": True}]},
        },
        context={
            "rollback_documented": True,
            "target_ambiguous": False,
            "data_sufficient": True,
            "has_explicit_approval_record": False,
            "has_false_positive_alternative": True,
        },
    )
    decision = adapter.evaluate(req)
    assert decision["result"] == "allow_proposal"
    reasons_text = " ".join(decision.get("reasons", []))
    assert "proposal emission" in reasons_text.lower() or "execution" in reasons_text.lower()
    assert req["candidate"].get("execution_requested") is False
    assert decision.get("policy_id")
    assert decision.get("policy_version")


def test_b0_containment_without_rollback_blocked_r5():
    """Proposta sem rollback → BLOQUEADA (R5)."""
    require_opa_or_fail_or_skip()
    adapter = OpaPolicyEngineAdapter()
    req = build_policy_request(
        request_id="SYNTH-REQ-R5-001",
        proposal_kind="containment",
        candidate={
            **_base_candidate(),
            "hypotheses": {"alternatives": [{"text": "SYNTH-FP", "is_false_positive": True}]},
        },
        context={
            "rollback_documented": False,
            "target_ambiguous": False,
            "data_sufficient": True,
            "has_explicit_approval_record": False,
            "has_false_positive_alternative": True,
        },
    )
    decision = adapter.evaluate(req)
    assert decision["result"] == "block_and_escalate"
    assert any("R5" in r for r in decision.get("reasons", []))
    assert not any("allow_proposal" == decision.get("result") for _ in [0])


def test_b0_containment_ambiguous_target_review_escalation_r2_r4():
    """Proposta com alvo ambíguo → revisão/escalonamento (R2/R4)."""
    require_opa_or_fail_or_skip()
    adapter = OpaPolicyEngineAdapter()
    req = build_policy_request(
        request_id="SYNTH-REQ-R2R4-001",
        proposal_kind="containment",
        candidate={
            **_base_candidate(),
            "hypotheses": {"alternatives": [{"text": "SYNTH-FP", "is_false_positive": True}]},
        },
        context={
            "rollback_documented": True,
            "target_ambiguous": True,
            "data_sufficient": True,
            "has_explicit_approval_record": False,
            "has_false_positive_alternative": True,
        },
    )
    decision = adapter.evaluate(req)
    assert decision["result"] == "block_and_escalate"
    reasons = decision.get("reasons", [])
    assert any("R2" in r or "R4" in r for r in reasons)
    assert any("ambig" in r.lower() or "escalat" in r.lower() or "R2/R4" in r for r in reasons)


def test_b0_query_proposal_incomplete_parameters_revision_r7():
    """Query sem janela temporal ou sem escopo explícito/parâmetros incompletos → revisão/bloqueio (R7).

    Semântica preservada (pré/pós migração Rego v1): política trata parâmetros incompletos de
    query_proposal como deny_block R7 com resultado block_and_escalate (exige revisão/metadados
    de bloqueio e escalonamento, sem execução).
    """
    require_opa_or_fail_or_skip()
    adapter = OpaPolicyEngineAdapter()
    req = build_policy_request(
        request_id="SYNTH-REQ-R7-001",
        proposal_kind="query_proposal",
        candidate={**_base_candidate(), "execution_requested": False},
        context={
            "query_parameters_complete": False,
        },
    )
    decision = adapter.evaluate(req)
    assert decision["result"] == "block_and_escalate"
    assert any("R7" in r for r in decision.get("reasons", []))
    assert "allow_proposal" != decision.get("result")
