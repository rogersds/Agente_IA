from __future__ import annotations

import os

import pytest

from soc_agent.adapters.policy_engine.opa_adapter import find_opa_binary


def require_opa_or_fail_or_skip():
    """Helper centralizado para testes dependentes de OPA.
    - REQUIRE_OPA=1 e OPA ausente: falha (nunca skip).
    - REQUIRE_OPA!=1 e OPA ausente: skip.
    - OPA presente: retorna caminho resolvido.
    """
    require_opa = os.getenv("REQUIRE_OPA") == "1"
    opa = find_opa_binary()
    if opa is None and require_opa:
        pytest.fail(
            "OPA CLI ausente mas REQUIRE_OPA=1; falha obrigatória (não skip). "
            "Defina PATH/OPA_BIN com OPA 1.22.4 pinado."
        )
    if opa is None:
        pytest.skip("opa CLI not available (REQUIRE_OPA!=1)")
    return opa
