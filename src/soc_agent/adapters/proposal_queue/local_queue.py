from __future__ import annotations

import json
from pathlib import Path
from threading import Lock
from typing import Any

from soc_agent.domain.common import utc_now_iso


class LocalActionProposalQueue:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        self._records: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                    pid = rec.get("proposal_id") or rec.get("query_proposal_id")
                    if pid:
                        self._records[pid] = rec
                except Exception:
                    pass

    def _append_line(self, rec: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()

    def _response(self, operation: str, status: str, proposal_id: str | None = None, proposal: dict[str, Any] | None = None, message: str | None = None) -> dict[str, Any]:
        out: dict[str, Any] = {"operation": operation, "status": status, "completed_at": utc_now_iso()}
        if proposal_id:
            out["proposal_id"] = proposal_id
        if proposal is not None:
            out["proposal"] = proposal
        if message:
            out["message"] = message
        return out

    def enqueue(self, proposal: dict[str, Any]) -> dict[str, Any]:
        pid = proposal.get("proposal_id") or proposal.get("query_proposal_id")
        if not pid:
            raise ValueError("proposal_id or query_proposal_id is required")
        with self._lock:
            self._records[pid] = dict(proposal)
            self._append_line(self._records[pid])
        return self._response("enqueue", "ok", proposal_id=pid, proposal=self._records[pid], message="enqueued")

    def update_status(self, request: dict[str, Any]) -> dict[str, Any]:
        # aceita payload direto ou envelope {"status_update": {...}}
        upd = request.get("status_update") if isinstance(request.get("status_update"), dict) else request
        pid = upd.get("proposal_id")
        if not pid:
            raise ValueError("proposal_id is required")
        with self._lock:
            if pid not in self._records:
                rec = {"proposal_id": pid}
            else:
                rec = dict(self._records[pid])
            for k, v in upd.items():
                if k in ("proposal_id", "status_update", "new_status", "operation", "requested_at"):
                    continue
                rec[k] = v
            # sincroniza estados comuns
            new_status = upd.get("new_status") or upd.get("status")
            if "approval_status" in upd:
                rec["approval_status"] = upd["approval_status"]
            elif new_status and "query_proposal_id" not in rec and "proposal_id" in rec:
                # containment: approval_status é o estado relevante
                rec["approval_status"] = new_status
            if "execution_status" in upd:
                rec["execution_status"] = upd["execution_status"]
            elif new_status and "query_proposal_id" in rec:
                rec["execution_status"] = new_status
            if upd.get("approval_record") is not None:
                rec["approval_record"] = upd["approval_record"]
                ar = upd["approval_record"] or {}
                if isinstance(ar, dict) and ar.get("decision") == "approved":
                    rec["approval_status"] = "approved"
                elif isinstance(ar, dict) and ar.get("decision") == "rejected":
                    rec["approval_status"] = "rejected"
            self._records[pid] = rec
            self._append_line(rec)
        return self._response("update_status", "ok", proposal_id=pid, proposal=self._records[pid], message="updated")

    def get(self, proposal_id: str) -> dict[str, Any]:
        proposal = self._records.get(proposal_id)
        status = "ok" if proposal is not None else "not_found"
        return self._response("get", status, proposal_id=proposal_id, proposal=proposal)
