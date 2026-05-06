from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .models import Profile
from .provider_registry import resolve_model_alias
from .utils import parse_json_safe, read_json, write_json

PROFILES_PATH = Path("profiles.json")
SUPPORTED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def load_profiles(path: Path = PROFILES_PATH) -> dict[str, dict[str, Any]]:
    data = read_json(path, {"profiles": {}})
    profiles = data.get("profiles", {})
    if isinstance(profiles, dict):
        return profiles
    return {}


def save_profiles(profiles: dict[str, dict[str, Any]], path: Path = PROFILES_PATH) -> None:
    write_json(path, {"profiles": profiles})


def get_profile(name: str, path: Path = PROFILES_PATH) -> Profile | None:
    profiles = load_profiles(path)
    raw = profiles.get(name)
    if not isinstance(raw, dict):
        return None
    return profile_from_dict(name, raw)


def add_profile(profile: Profile, path: Path = PROFILES_PATH) -> None:
    profiles = load_profiles(path)
    if profile.name in profiles:
        raise ValueError(f"Profile '{profile.name}' already exists")
    profiles[profile.name] = profile_to_storage(profile)
    save_profiles(profiles, path)


def update_profile(name: str, updates: dict[str, Any], path: Path = PROFILES_PATH) -> Profile:
    profiles = load_profiles(path)
    if name not in profiles:
        raise ValueError(f"Profile '{name}' not found")

    current = dict(profiles[name])
    for key, value in updates.items():
        if value is not None:
            current[key] = value

    updated = profile_from_dict(name, current)
    profiles[name] = profile_to_storage(updated)
    save_profiles(profiles, path)
    return updated


def delete_profile(name: str, path: Path = PROFILES_PATH) -> None:
    profiles = load_profiles(path)
    if name not in profiles:
        raise ValueError(f"Profile '{name}' not found")
    del profiles[name]
    save_profiles(profiles, path)


def profile_from_dict(name: str, raw: dict[str, Any]) -> Profile:
    return Profile(
        name=name,
        base_url=str(raw.get("base_url", "")),
        endpoint=str(raw.get("endpoint", "/completion")),
        method=str(raw.get("method", "POST")).upper(),
        payload_template=raw.get("payload_template", {"prompt": "{{prompt}}"}),
        headers=raw.get("headers", {}) or {},
        cookies=raw.get("cookies", {}) or {},
        prompt_field_candidates=raw.get("prompt_field_candidates", ["prompt", "message", "input", "query", "messages"]),
        response_text_paths=raw.get("response_text_paths", []) or [],
        timeout=int(raw.get("timeout", 60)),
        notes=raw.get("notes"),
        stream=bool(raw.get("stream", True)),
        model=raw.get("model") or None,
    )


def profile_to_storage(profile: Profile) -> dict[str, Any]:
    payload = asdict(profile)
    payload.pop("name", None)
    return payload


def validate_profile(profile: Profile, strict: bool = False) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not profile.name.strip():
        errors.append("name is required")

    # When a model alias is registered, the provider registry supplies base_url/endpoint.
    selected_model = profile.model or profile.name
    provider_spec = resolve_model_alias(selected_model)

    if not provider_spec:
        if not profile.base_url.strip():
            errors.append("base_url is required")
        else:
            parsed = urlparse(profile.base_url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                errors.append("base_url must be a valid http(s) URL")

        if not profile.endpoint:
            errors.append("endpoint is required")
        elif not (
            profile.endpoint.startswith("/")
            or profile.endpoint.startswith("http://")
            or profile.endpoint.startswith("https://")
        ):
            errors.append("endpoint must start with '/' or be an absolute URL")

    if profile.method.upper() not in SUPPORTED_METHODS:
        errors.append(
            f"method must be one of {', '.join(sorted(SUPPORTED_METHODS))}"
        )

    if not isinstance(profile.headers, dict):
        errors.append("headers must be a dictionary")

    if not isinstance(profile.cookies, dict):
        errors.append("cookies must be a dictionary")

    if not isinstance(profile.response_text_paths, list):
        errors.append("response_text_paths must be a list")

    if not isinstance(profile.prompt_field_candidates, list):
        errors.append("prompt_field_candidates must be a list")

    if profile.timeout < 1:
        errors.append("timeout must be >= 1")

    if not provider_spec:
        template_json = json.dumps(profile.payload_template)
        has_prompt_placeholder = "{{prompt}}" in template_json or "{{messages}}" in template_json
        if not has_prompt_placeholder:
            errors.append("payload_template must include {{prompt}} or {{messages}}")

    if strict and not profile.response_text_paths:
        warnings.append("strict mode: response_text_paths is empty")

    if not profile.response_text_paths:
        warnings.append("response_text_paths is empty; fallback extraction will be used")

    return errors, warnings


def parse_payload_template(template_text: str) -> dict[str, Any]:
    parsed = parse_json_safe(template_text)
    if not isinstance(parsed, dict):
        raise ValueError("payload template must be a valid JSON object")
    return parsed
