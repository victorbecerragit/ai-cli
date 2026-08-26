# src/ai_cli/api_client.py
from __future__ import annotations

import os
import time
from typing import Any, Generator
from urllib.parse import urlencode

import requests

from .models import ApiResult, Profile
from .provider_registry import ProviderSpec, resolve_model_alias
from .utils import build_url, deep_replace_tokens, get_by_dotted_path, parse_json_safe, truncate

COMMON_JSON_TEXT_FIELDS = [
    "text",
    "response",
    "answer",
    "content",
    "message",
    "output",
    "choices.0.message.content",
    "choices.0.delta.content",
    "candidates.0.content.parts.0.text",
]


class ApiClient:
    def __init__(
        self,
        profile: Profile,
        cookies: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout_seconds: int | None = None,
        model_override: str | None = None,
    ) -> None:
        self.profile = profile
        self.model_override = model_override
        self.cookies = dict(profile.cookies)
        if cookies:
            self.cookies.update(cookies)
        self.timeout_seconds = timeout_seconds or profile.timeout
        self.extra_headers = extra_headers or {}

    def ask(self, prompt: str, history: list[dict[str, str]] | None = None, stream: bool | None = None) -> ApiResult:
        history = history or []
        method, url, payload, headers, response_text_paths, use_stream = self._prepare_request(
            prompt, history, stream
        )

        started = time.monotonic()
        response = requests.request(
            method,
            url,
            json=payload,
            headers=headers,
            cookies=self.cookies,
            timeout=self.timeout_seconds,
            stream=use_stream,
        )

        content_type = response.headers.get("content-type", "")

        if use_stream and "event-stream" in content_type.lower():
            text, raw_preview = _consume_sse(response, response_text_paths)
        elif use_stream and response.headers.get("transfer-encoding", "").lower() == "chunked":
            text, raw_preview = _consume_chunks(response, response_text_paths)
        else:
            raw = response.text
            text = _extract_text(raw, content_type, response_text_paths)
            raw_preview = truncate(raw)

        elapsed_ms = int((time.monotonic() - started) * 1000)
        return ApiResult(
            ok=response.ok,
            status_code=response.status_code,
            text=text,
            elapsed_ms=elapsed_ms,
            raw_preview=raw_preview,
            content_type=content_type,
        )

    def ask_stream(self, prompt: str, history: list[dict[str, str]] | None = None) -> Generator[str, None, None]:
        history = history or []
        method, url, payload, headers, response_text_paths, use_stream = self._prepare_request(
            prompt, history, stream=True
        )

        response = requests.request(
            method,
            url,
            json=payload,
            headers=headers,
            cookies=self.cookies,
            timeout=self.timeout_seconds,
            stream=use_stream,
        )

        content_type = response.headers.get("content-type", "").lower()
        if use_stream and "event-stream" in content_type:
            yield from _yield_sse_text(response, response_text_paths)
        elif use_stream and response.headers.get("transfer-encoding", "").lower() == "chunked":
            yield from response.iter_content(chunk_size=None, decode_unicode=True)
        else:
            raw = response.text
            yield _extract_text(raw, content_type, response_text_paths)

    def _prepare_request(
        self, prompt: str, history: list[dict[str, str]], stream: bool | None = None
    ) -> tuple[str, str, dict[str, Any], dict[str, str], list[str], bool]:
        selected_model = self.model_override or self.profile.model or self.profile.name
        provider_spec = resolve_model_alias(selected_model)

        url = build_url(self.profile.base_url, self.profile.endpoint)
        payload = self._build_payload(prompt, history)
        method = self.profile.method
        response_text_paths = list(self.profile.response_text_paths)

        headers = {"accept": "application/json, text/event-stream, text/plain, */*", "content-type": "application/json"}
        headers.update(self.profile.headers)
        headers.update(self.extra_headers)

        if provider_spec:
            url = build_url(provider_spec.base_url, provider_spec.endpoint)
            method = provider_spec.method
            payload = self._build_provider_payload(provider_spec, prompt, history)
            if provider_spec.response_text_paths:
                response_text_paths = list(provider_spec.response_text_paths)
            headers = self._inject_provider_auth(headers, provider_spec)
            if provider_spec.auth_query_param and provider_spec.auth_env:
                api_key = os.getenv(provider_spec.auth_env)
                if api_key:
                    url = f"{url}?{urlencode({provider_spec.auth_query_param: api_key})}"

        if provider_spec and provider_spec.payload_style == "google-generate-content":
            # Google requires a different action suffix and alt=sse for streaming
            use_stream = self.profile.stream if stream is None else stream
            if use_stream:
                url = url.replace(":generateContent", ":streamGenerateContent")
                separator = "&" if "?" in url else "?"
                url = f"{url}{separator}alt=sse"
        else:
            use_stream = self.profile.stream if stream is None else stream

        return method, url, payload, headers, response_text_paths, use_stream

    def _build_payload(self, prompt: str, history: list[dict[str, str]]) -> dict[str, Any]:
        messages = [*history, {"role": "user", "content": prompt}]

        if self.profile.payload_template:
            rendered = deep_replace_tokens(self.profile.payload_template, prompt, messages)
            if isinstance(rendered, dict):
                return rendered

        return {"messages": messages}

    def _build_provider_payload(
        self,
        provider_spec: ProviderSpec,
        prompt: str,
        history: list[dict[str, str]],
    ) -> dict[str, Any]:
        if provider_spec.payload_style == "google-generate-content":
            messages = [*history, {"role": "user", "content": prompt}]
            contents: list[dict[str, Any]] = []
            system_parts: list[dict[str, str]] = []

            for msg in messages:
                role = (msg.get("role") or "user").strip().lower()
                content = msg.get("content", "")

                if not isinstance(content, str) or not content.strip():
                    continue

                if role == "system":
                    system_parts.append({"text": content})
                    continue

                gemini_role = "model" if role == "assistant" else "user"
                contents.append(
                    {
                        "role": gemini_role,
                        "parts": [{"text": content}],
                    }
                )

            payload: dict[str, Any] = {"contents": contents}
            if system_parts:
                payload["systemInstruction"] = {"parts": system_parts}
            return payload

        return self._build_payload(prompt, history)

    def _inject_provider_auth(self, headers: dict[str, str], provider_spec: ProviderSpec) -> dict[str, str]:
        if not provider_spec.auth_env:
            return headers

        value = os.getenv(provider_spec.auth_env)
        if not value:
            return headers

        if provider_spec.auth_header:
            lower_headers = {k.lower(): v for k, v in headers.items()}
            if provider_spec.auth_header.lower() not in lower_headers:
                headers[provider_spec.auth_header] = value

        return headers


def _consume_sse(response: requests.Response, response_text_paths: list[str]) -> tuple[str, str | None]:
    chunks: list[str] = []
    raw_lines: list[str] = []

    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.strip():
            continue
        raw_lines.append(line)

        stripped = line.strip().lower()
        if not stripped.startswith("data:"):
            continue

        # Extract everything after "data:"
        payload = line.strip()[len("data:"):].strip()
        # Google sometimes ends with a line that isn't exactly [DONE] but empty
        if payload.upper() == "[DONE]" or not payload:
            break

        parsed = parse_json_safe(payload)
        if isinstance(parsed, dict):
            # Try profile-specific paths first
            found = False
            for path in response_text_paths:
                val = get_by_dotted_path(parsed, path)
                if isinstance(val, str):
                    if val.upper() != "[DONE]":
                        chunks.append(val)
                    found = True
                    break
            
            if found:
                continue

            google_text = _extract_google_candidate_text(parsed)
            if google_text:
                if google_text.upper() != "[DONE]":
                    chunks.append(google_text)
                continue

        # Only append raw payload if it's not the terminal [DONE] signal
        if payload and payload != "[DONE]":
            chunks.append(payload)

    combined = "".join(chunks).strip()
    if combined.endswith("[DONE]"):
        combined = combined[:-6].strip()
    raw_preview = truncate("\n".join(raw_lines))
    return (combined or "<empty response>"), raw_preview

def _yield_sse_text(response: requests.Response, response_text_paths: list[str]) -> Generator[str, None, None]:
    for line in response.iter_lines(decode_unicode=True):
        if not line or not line.strip():
            continue

        stripped = line.strip()
        if not stripped.lower().startswith("data:"):
            continue

        # Extract everything after "data:"
        payload = stripped[len("data:"):].strip()
        if payload.upper() == "[DONE]" or not payload:
            break

        parsed = parse_json_safe(payload)
        if isinstance(parsed, dict):
            found = False
            for path in response_text_paths:
                val = get_by_dotted_path(parsed, path)
                if isinstance(val, str):
                    if val.upper() != "[DONE]":
                        yield val
                    found = True
                    break
            if found:
                continue

            google_text = _extract_google_candidate_text(parsed)
            if google_text:
                if google_text.upper() != "[DONE]":
                    yield google_text
                continue

        if payload and payload != "[DONE]":
            yield payload

def _consume_chunks(response: requests.Response, response_text_paths: list[str]) -> tuple[str, str | None]:
    pieces: list[str] = []
    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
        if not chunk:
            continue
        pieces.append(chunk)
    raw = "".join(pieces)
    text = _extract_text(raw, response.headers.get("content-type", ""), response_text_paths=response_text_paths)
    return text, truncate(raw)


def _extract_google_candidate_text(parsed: Any) -> str:
    if not isinstance(parsed, dict):
        return ""

    candidates = parsed.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""

    first = candidates[0]
    if not isinstance(first, dict):
        return ""

    content = first.get("content")
    if not isinstance(content, dict):
        return ""

    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""

    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                texts.append(text)

    return "".join(texts).strip()


def _extract_text(raw_text: str, content_type: str, response_text_paths: list[str]) -> str:
    lower_ct = (content_type or "").lower()

    if "application/json" in lower_ct or raw_text.strip().startswith("{") or raw_text.strip().startswith("["):
        parsed = parse_json_safe(raw_text)
        if parsed is not None:
            for path in response_text_paths:
                value = get_by_dotted_path(parsed, path)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            for path in COMMON_JSON_TEXT_FIELDS:
                value = get_by_dotted_path(parsed, path)
                if isinstance(value, str) and value.strip():
                    return value.strip()

            google_text = _extract_google_candidate_text(parsed)
            if google_text:
                return google_text

            if isinstance(parsed, dict):
                prompt_feedback = parsed.get("promptFeedback")
                if isinstance(prompt_feedback, dict):
                    block_reason = prompt_feedback.get("blockReason")
                    if isinstance(block_reason, str) and block_reason.strip():
                        return f"<blocked: {block_reason}>"

            return truncate(raw_text, 1200) or "<empty response>"

    if "text/event-stream" in lower_ct:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip().startswith("data:")]
        events = []
        for line in lines:
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            parsed = parse_json_safe(payload)
            if isinstance(parsed, dict):
                google_text = _extract_google_candidate_text(parsed)
                if google_text:
                    events.append(google_text)
                    continue
                if isinstance(parsed.get("content"), str):
                    events.append(parsed["content"])
                    continue
            events.append(payload)
        result = "".join(events).strip()
        return result or "<empty response>"

    text = raw_text.strip()
    return text or "<empty response>"