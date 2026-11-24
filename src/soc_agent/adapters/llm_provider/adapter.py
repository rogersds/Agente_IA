from __future__ import annotations

from typing import Any

from soc_agent.domain.common import utc_now_iso


class LocalDeterministicLlmProvider:
    """Pilot/local adapter: no external provider knowledge leaks to core.
    Produces structured, deterministic output for tests/pilot flows without credentials.
    """

    model_version = "local-deterministic-0.1"
    prompt_version = "prompt-v1"

    def generate(self, request: dict[str, Any]) -> dict[str, Any]:
        purpose = (request.get("purpose") or "analysis").lower()
        prompt = request.get("prompt") or request.get("input") or ""
        text = prompt if isinstance(prompt, str) else str(prompt)
        # Deterministic structured content; real providers can replace this adapter.
        content: dict[str, Any] = {
            "purpose": purpose,
            "summary": text[:500],
            "notes": ["Deterministic local adapter output; validate against domain schemas before acceptance."],
        }
        return {
            "response_id": request.get("request_id", "llm-resp"),
            "generated_at": utc_now_iso(),
            "model_version": self.model_version,
            "prompt_version": self.prompt_version,
            "content": content,
            "raw": None,
        }
