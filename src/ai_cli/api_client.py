from __future__ import annotations

import time
from typing import Any

import requests

from .models import ApiResult, Profile
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
]


class ApiClient:
    def __init__(
        self,
        profile: Profile,
        cookies: dict[str, str] | None = None,
        extra_headers: dict[str, str] | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.profile = profile
        self.cookies = dict(profile.cookies)
        if cookies:
            self.cookies.update(cookies)
        self.timeout_seconds = timeout_seconds or profile.timeout
        self.extra_headers = extra_headers or {}

    def ask(self, prompt: str, history: list[dict[str, str]] | None = None, stream: bool | None = None) -> ApiResult:
        history = history or []
        url = build_url(self.profile.base_url, self.profile.endpoint)
        payload = self._build_payload(prompt, history)

        headers = {
            "accept": "application/json, text/event-stream, text/plain, */*",
            "content-type": "application/json",
        }
        headers.update(self.profile.headers)
        headers.update(self.extra_headers)

        use_stream = self.profile.stream if stream is None else stream

        started = time.monotonic()
        response = requests.request(
            self.profile.method,
            url,
            json=payload,
            headers=headers,
            cookies=self.cookies,
            timeout=self.timeout_seconds,
            stream=use_stream,
        )

        content_type = response.headers.get("content-type", "")

        if use_stream and "event-stream" in content_type.lower():
            text, raw_preview = _consume_sse(response)
        elif use_stream and response.headers.get("transfer-encoding", "").lower() == "chunked":
            text, raw_preview = _consume_chunks(response)
        else:
            raw = response.text
            text = _extract_text(raw, content_type, self.profile.response_text_paths)
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

    def _build_payload(self, prompt: str, history: list[dict[str, str]]) -> dict[str, Any]:
        messages = [*history, {"role": "user", "content": prompt}]

        if self.profile.payload_template:
            rendered = deep_replace_tokens(self.profile.payload_template, prompt, messages)
            if isinstance(rendered, dict):
                return rendered

        # Fallback candidate that works for many demos.
        return {"messages": messages}


def _consume_sse(response: requests.Response) -> tuple[str, str | None]:
    chunks: list[str] = []
    raw_lines: list[str] = []

    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        raw_lines.append(line)

        if not line.startswith("data:"):
            continue

        payload = line[5:].strip()
        if payload == "[DONE]":
            break

        parsed = parse_json_safe(payload)
        if isinstance(parsed, dict):
            content = parsed.get("content")
            if isinstance(content, str):
                chunks.append(content)
                continue

        chunks.append(payload)

    combined = "".join(chunks).strip()
    raw_preview = truncate("\n".join(raw_lines))
    return (combined or "<empty response>"), raw_preview


def _consume_chunks(response: requests.Response) -> tuple[str, str | None]:
    pieces: list[str] = []
    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
        if not chunk:
            continue
        pieces.append(chunk)
    raw = "".join(pieces)
    text = _extract_text(raw, response.headers.get("content-type", ""), response_text_paths=[])
    return text, truncate(raw)


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

            return truncate(raw_text, 1200) or "<empty response>"

    if "text/event-stream" in lower_ct:
        # Non-stream fallback: parse SSE from raw text.
        lines = [line.strip() for line in raw_text.splitlines() if line.strip().startswith("data:")]
        events = []
        for line in lines:
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            parsed = parse_json_safe(payload)
            if isinstance(parsed, dict) and isinstance(parsed.get("content"), str):
                events.append(parsed["content"])
            else:
                events.append(payload)
        result = "".join(events).strip()
        return result or "<empty response>"

    text = raw_text.strip()
    if text:
        return text
    return "<empty response>"
