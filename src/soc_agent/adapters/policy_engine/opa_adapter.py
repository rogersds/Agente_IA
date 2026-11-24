from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from soc_agent.contracts_runtime.loader import get_policy_dir
from soc_agent.domain.common import utc_now_iso
from soc_agent.domain.policy import normalize_policy_decision


def _is_usable_opa_path(candidate: str | None) -> bool:
    if not candidate:
        return False
    p = Path(candidate)
    if not p.is_file():
        return False
    return os.access(p, os.X_OK) or os.name == "nt"


def find_opa_binary(opa_bin_env: str | None = None) -> str | None:
    """Descoberta centralizada do OPA: OPA_BIN válido (executável) tem precedência; senão `opa` no PATH."""
    configured = opa_bin_env if opa_bin_env is not None else os.environ.get("OPA_BIN")
    if configured:
        if _is_usable_opa_path(configured):
            return str(Path(configured))
        on_path = shutil.which(configured)
        if on_path and _is_usable_opa_path(on_path):
            return on_path
        # OPA_BIN definido mas inválido/não utilizável: fallback para PATH
    return shutil.which("opa")


class OpaPolicyEngineAdapter:
    def __init__(self, policy_path: Path | None = None, opa_bin: str | None = None):
        self.policy_path = policy_path or (get_policy_dir() / "action_proposal.rego")
        resolved = opa_bin or find_opa_binary()
        self.opa_bin = resolved or opa_bin or os.environ.get("OPA_BIN") or "opa"

    def evaluate(self, request: dict[str, Any]) -> dict[str, Any]:
        # R2/R4/R5/R7 safety: fail closed if policy engine cannot be evaluated
        if not self.policy_path.is_file():
            return self._blocked(request, ["policy_file_missing: fail closed"])
        resolved_opa = find_opa_binary(self.opa_bin) or (self.opa_bin if _is_usable_opa_path(self.opa_bin) else shutil.which(self.opa_bin))
        if resolved_opa is None:
            return self._blocked(request, [f"opa_cli_unavailable:{self.opa_bin}: fail closed"])
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
            json.dump(request, tf, ensure_ascii=False)
            input_path = tf.name
        try:
            query = "data.soc_agent.policy.action_proposal.decision"
            cmd = [resolved_opa, "eval", "-d", str(self.policy_path), "-i", input_path, "--format", "json", query]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode != 0:
                return self._blocked(request, [f"opa_eval_error: {proc.stderr.strip() or proc.stdout.strip() or 'unknown'}"])
            data = json.loads(proc.stdout or "{}")
            result_expr = (((data.get("result") or [{}])[0]).get("expressions") or [{}])[0].get("value") or {}
            if not isinstance(result_expr, dict):
                result_expr = {}
            decision = normalize_policy_decision(result_expr, request)
            # ensure policy metadata
            if decision.get("policy_version") in (None, "", "unknown"):
                decision["policy_version"] = "action_proposal.rego"
            if decision.get("policy_id") in (None, ""):
                decision["policy_id"] = "soc_agent.policy.action_proposal"
            if not decision.get("evaluated_at"):
                decision["evaluated_at"] = utc_now_iso()
            return decision
        except Exception as e:
            return self._blocked(request, [f"policy_evaluation_exception: {e}"])
        finally:
            try:
                os.unlink(input_path)
            except Exception:
                pass

    def _blocked(self, request: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
        return normalize_policy_decision(
            {
                "result": "block_and_escalate",
                "reasons": reasons,
                "required_actions": ["escalate_to_authorized_human", "record_audit_event"],
                "policy_id": "soc_agent.policy.action_proposal",
                "policy_version": "unavailable",
                "evaluated_at": utc_now_iso(),
                "input_ref": {"request_id": request.get("request_id"), "proposal_kind": request.get("proposal_kind")},
            },
            request,
        )
