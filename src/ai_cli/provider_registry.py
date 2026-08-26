# src/ai_cli/provider_registry.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSpec:
    provider: str
    alias: str
    model_id: str
    base_url: str
    endpoint: str
    method: str = "POST"
    auth_header: str | None = None
    auth_query_param: str | None = None
    auth_env: str | None = None
    payload_style: str = "openai-chat"
    response_text_paths: tuple[str, ...] = ()


def _google_generate_content_spec(alias: str, model_id: str) -> ProviderSpec:
    return ProviderSpec(
        provider="google",
        alias=alias,
        model_id=model_id,
        base_url="https://generativelanguage.googleapis.com",
        endpoint=f"/v1beta/models/{model_id}:generateContent",
        method="POST",
        auth_header=None,
        auth_query_param="key",
        auth_env="GEMINI_API_KEY",
        payload_style="google-generate-content",
        response_text_paths=("candidates.0.content.parts.0.text",),
    )


_PROVIDER_ALIASES: dict[str, ProviderSpec] = {
    "google/gemma4": _google_generate_content_spec("google/gemma4", "gemma-4-26b-a4b-it"),
    "google/gemma-4-26b-a4b-it": _google_generate_content_spec(
        "google/gemma-4-26b-a4b-it", "gemma-4-26b-a4b-it"
    ),
    "google/gemma-4-31b-it": _google_generate_content_spec(
        "google/gemma-4-31b-it", "gemma-4-31b-it"
    ),
}


def resolve_model_alias(model_name: str | None) -> ProviderSpec | None:
    if not model_name:
        return None
    return _PROVIDER_ALIASES.get(model_name.strip().lower())
