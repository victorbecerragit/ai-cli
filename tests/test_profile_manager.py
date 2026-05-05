from __future__ import annotations

from pathlib import Path

from ai_cli.models import Profile
from ai_cli.profile_manager import (
    add_profile,
    delete_profile,
    get_profile,
    load_profiles,
    update_profile,
    validate_profile,
)


def test_profile_crud_roundtrip(tmp_path: Path) -> None:
    profiles_path = tmp_path / "profiles.json"
    profile = Profile(name="demo", base_url="https://example.com")

    add_profile(profile, path=profiles_path)

    loaded = get_profile("demo", path=profiles_path)
    assert loaded is not None
    assert loaded.base_url == "https://example.com"

    updated = update_profile("demo", {"timeout": 90, "endpoint": "/chat"}, path=profiles_path)
    assert updated.timeout == 90
    assert updated.endpoint == "/chat"

    all_profiles = load_profiles(path=profiles_path)
    assert "demo" in all_profiles

    delete_profile("demo", path=profiles_path)
    assert get_profile("demo", path=profiles_path) is None


def test_validate_profile_requires_prompt_or_messages_token() -> None:
    invalid = Profile(
        name="invalid",
        base_url="https://example.com",
        payload_template={"static": "value"},
    )

    errors, warnings = validate_profile(invalid)

    assert any("payload_template" in error for error in errors)
    assert isinstance(warnings, list)
