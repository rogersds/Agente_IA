from __future__ import annotations

from typing import Any, Protocol


class ActionProposalQueue(Protocol):
    def enqueue(self, proposal: dict[str, Any]) -> dict[str, Any]: ...

    def update_status(self, request: dict[str, Any]) -> dict[str, Any]: ...

    def get(self, proposal_id: str) -> dict[str, Any]: ...
