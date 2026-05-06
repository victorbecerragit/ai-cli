from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Profile:
    name: str
    base_url: str
    endpoint: str = "/completion"
    method: str = "POST"
    payload_template: dict[str, Any] = field(default_factory=lambda: {"prompt": "{{prompt}}"})
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    prompt_field_candidates: list[str] = field(
        default_factory=lambda: ["prompt", "message", "input", "query", "messages"]
    )
    response_text_paths: list[str] = field(default_factory=list)
    timeout: int = 60
    notes: str | None = None
    stream: bool = True
    model: str | None = None


@dataclass
class ProbeEvent:
    kind: str
    timestamp: str
    method: str | None = None
    url: str | None = None
    path: str | None = None
    resource_type: str | None = None
    status: int | None = None
    request_headers: dict[str, str] = field(default_factory=dict)
    response_headers: dict[str, str] = field(default_factory=dict)
    request_body_preview: str | None = None
    response_body_preview: str | None = None
    transport: str | None = None
    message: str | None = None


@dataclass
class ApiResult:
    ok: bool
    status_code: int | None
    text: str
    elapsed_ms: int
    raw_preview: str | None = None
    content_type: str | None = None
