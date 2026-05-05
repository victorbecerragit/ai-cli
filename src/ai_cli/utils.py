from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

MAX_PREVIEW_CHARS = 500


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def truncate(value: str | None, max_chars: int = MAX_PREVIEW_CHARS) -> str | None:
    if value is None:
        return None
    if len(value) <= max_chars:
        return value
    return f"{value[:max_chars]}... <truncated>"


def parse_json_safe(text: str) -> Any:
    try:
        return json.loads(text)
    except Exception:
        return None


def as_jsonable(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    if isinstance(value, list):
        return [as_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: as_jsonable(v) for k, v in value.items()}
    return value


def write_json(path: str | Path, payload: Any) -> None:
    p = Path(path)
    p.write_text(json.dumps(as_jsonable(payload), indent=2), encoding="utf-8")


def read_json(path: str | Path, default: Any) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def normalize_endpoint(endpoint: str) -> str:
    endpoint = endpoint.strip()
    if not endpoint:
        return "/"
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    return endpoint


def build_url(base_url: str, endpoint: str) -> str:
    endpoint = normalize_endpoint(endpoint)
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return urljoin(base_url.rstrip("/") + "/", endpoint.lstrip("/"))


def origin_from_url(url: str) -> str:
    parts = urlparse(url)
    if not parts.scheme or not parts.netloc:
        return ""
    return f"{parts.scheme}://{parts.netloc}"


def deep_replace_tokens(value: Any, prompt: str, messages: list[dict[str, str]]) -> Any:
    if isinstance(value, str):
        if value == "{{prompt}}":
            return prompt
        if value == "{{messages}}":
            return messages
        return value.replace("{{prompt}}", prompt)

    if isinstance(value, list):
        return [deep_replace_tokens(v, prompt, messages) for v in value]

    if isinstance(value, dict):
        return {k: deep_replace_tokens(v, prompt, messages) for k, v in value.items()}

    return value


def parse_header_pairs(items: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in items:
        if ":" not in item:
            continue
        k, v = item.split(":", 1)
        parsed[k.strip()] = v.strip()
    return parsed


def parse_cookie_pairs(items: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        parsed[k.strip()] = v.strip()
    return parsed


def get_by_dotted_path(payload: Any, dotted_path: str) -> Any:
    cursor = payload
    for part in dotted_path.split("."):
        if isinstance(cursor, dict):
            cursor = cursor.get(part)
        elif isinstance(cursor, list) and part.isdigit():
            idx = int(part)
            if idx >= len(cursor):
                return None
            cursor = cursor[idx]
        else:
            return None
    return cursor
