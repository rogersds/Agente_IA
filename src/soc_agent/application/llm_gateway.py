from __future__ import annotations

from typing import Any

from soc_agent.ports.llm_provider import LlmProvider


def generate_structured(provider: LlmProvider, request: dict[str, Any]) -> dict[str, Any]:
    # Central point to attach/propagate version metadata and validate envelope in future
    response = provider.generate(request)
    if "model_version" not in response:
        response["model_version"] = getattr(provider, "model_version", None)
    if "prompt_version" not in response:
        response["prompt_version"] = getattr(provider, "prompt_version", None)
    return response
