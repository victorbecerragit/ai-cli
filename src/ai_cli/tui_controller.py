from __future__ import annotations

from pathlib import Path
from typing import Generator

from .api_client import ApiClient
from .models import ApiResult, Profile
from .profile_manager import get_profile, load_profiles, profile_from_dict
from .utils import build_url, deep_replace_tokens, now_iso, write_json


class TuiController:
    def __init__(self, start_profile: str | None = None) -> None:
        self.start_profile = start_profile
        self.active_profile_name: str | None = None
        self.history: list[dict[str, str]] = []
        self.transcript: list[dict[str, str]] = []
        self.last_debug: dict[str, object] = {
            "status": "ready",
            "profile": None,
        }

    def clear_chat_state(self) -> None:
        self.history.clear()
        self.transcript.clear()

    def load_profiles(self) -> tuple[list[Profile], str | None]:
        profiles = load_profiles()
        ordered_profiles = [profile_from_dict(name, profiles[name]) for name in sorted(profiles.keys())]

        if not ordered_profiles:
            self.active_profile_name = None
            self.last_debug = {
                "status": "no-profiles",
                "hint": "Use `ai-cli profiles add <name>` to create a profile.",
            }
            return ordered_profiles, None

        names = [p.name for p in ordered_profiles]
        selected = self.start_profile if self.start_profile in names else names[0]
        self.active_profile_name = selected

        selected_profile = get_profile(selected)
        if selected_profile:
            self.last_debug = self._debug_profile_ready(selected_profile)

        return ordered_profiles, selected

    def select_profile(self, selected_name: str) -> Profile | None:
        self.active_profile_name = selected_name
        profile = get_profile(selected_name)
        if profile:
            self.last_debug = {
                "status": "profile-selected",
                "profile": profile.name,
                "base_url": profile.base_url,
                "endpoint": profile.endpoint,
                "method": profile.method,
                "timeout": profile.timeout,
            }
        return profile

    def active_profile(self) -> Profile | None:
        if not self.active_profile_name:
            return None
        return get_profile(self.active_profile_name)

    def mark_request_in_flight(self, profile: Profile, prompt: str) -> None:
        request_payload = deep_replace_tokens(
            profile.payload_template,
            prompt,
            [*self.history, {"role": "user", "content": prompt}],
        )
        self.last_debug = {
            "status": "in-flight",
            "profile": profile.name,
            "url": build_url(profile.base_url, profile.endpoint),
            "method": profile.method,
            "timeout": profile.timeout,
            "payload_preview": request_payload,
        }

    def ask_sync(self, profile: Profile, prompt: str) -> ApiResult:
        client = ApiClient(profile)
        result = client.ask(prompt, history=self.history)

        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": result.text})
        self.transcript.append({"role": "user", "content": prompt})
        self.transcript.append({"role": "assistant", "content": result.text})

        self.last_debug = {
            "status": "ok" if result.ok else "error",
            "profile": profile.name,
            "url": build_url(profile.base_url, profile.endpoint),
            "method": profile.method,
            "timeout": profile.timeout,
            "status_code": result.status_code,
            "elapsed_ms": result.elapsed_ms,
            "content_type": result.content_type,
            "response_preview": result.raw_preview,
        }
        return result

    def ask_stream(self, profile: Profile, prompt: str) -> Generator[str, None, None]:
        client = ApiClient(profile)
        return client.ask_stream(prompt, history=self.history)

    def update_history(self, prompt: str, assistant_response: str) -> None:
        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": assistant_response})
        self.transcript.append({"role": "user", "content": prompt})
        self.transcript.append({"role": "assistant", "content": assistant_response})

    def mark_exception(self, profile: Profile, error: Exception) -> None:
        self.last_debug = {
            "status": "exception",
            "profile": profile.name,
            "error": str(error),
        }

    def save_transcript(self) -> str:
        file_name = f"tui-transcript-{now_iso().replace(':', '-').replace('+', '_')}.json"
        payload = {
            "saved_at": now_iso(),
            "profile": self.active_profile_name,
            "transcript": self.transcript,
            "history": self.history,
        }
        write_json(Path(file_name), payload)
        return file_name

    def _debug_profile_ready(self, profile: Profile) -> dict[str, object]:
        return {
            "status": "ready",
            "profile": profile.name,
            "base_url": profile.base_url,
            "endpoint": profile.endpoint,
            "method": profile.method,
            "timeout": profile.timeout,
        }
