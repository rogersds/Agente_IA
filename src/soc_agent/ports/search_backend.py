from __future__ import annotations

from typing import Any, Protocol


class SearchBackend(Protocol):
    def search(self, request: dict[str, Any]) -> dict[str, Any]: ...
