from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

if TYPE_CHECKING:
    from playwright.sync_api import Playwright, Request, Response, WebSocket

from .models import ProbeEvent
from .utils import now_iso, truncate, write_json

HTTP_HEADER_ALLOWLIST = {
    "content-type",
    "accept",
    "authorization",
    "user-agent",
    "origin",
    "referer",
}

AI_PATH_KEYWORDS = ["/completion", "/completions", "/chat", "/api/chat", "/generate", "/inference"]


def _pick_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() in HTTP_HEADER_ALLOWLIST}


def _detect_transport(content_type: str, url: str) -> str:
    lower_ct = (content_type or "").lower()
    lower_url = (url or "").lower()
    if "event-stream" in lower_ct:
        return "sse"
    if "application/json" in lower_ct:
        return "json"
    if lower_url.startswith("ws://") or lower_url.startswith("wss://"):
        return "websocket"
    if "text/plain" in lower_ct:
        return "text"
    return "unknown"


def _path_from_url(url: str) -> str:
    try:
        return urlparse(url).path or "/"
    except Exception:
        return "/"


def _is_likely_ai(url: str) -> bool:
    lower = (url or "").lower()
    return any(keyword in lower for keyword in AI_PATH_KEYWORDS)


def probe_url(
    url: str,
    timeout_seconds: int = 12,
    headless: bool = False,
    contains: str | None = None,
    output: str | None = None,
) -> dict[str, Any]:
    events: list[ProbeEvent] = []
    likely_ai: dict[str, dict[str, Any]] = {}

    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    with sync_playwright() as pw:
        _capture(pw, url, timeout_seconds, headless, events)

    filtered = _filter_events(events, contains)

    for event in filtered:
        if event.url and _is_likely_ai(event.url):
            likely_ai[event.url] = {
                "url": event.url,
                "path": event.path,
                "transport": event.transport,
                "method": event.method,
            }

    payload = {
        "meta": {
            "tool": "mini-devtools-probe",
            "captured_at": now_iso(),
            "url": url,
            "timeout_seconds": timeout_seconds,
            "contains": contains,
        },
        "likely_endpoints": list(likely_ai.values()),
        "events": [asdict(e) for e in filtered],
    }

    if output:
        write_json(output, payload)

    return payload


def bootstrap_session(
    url: str, endpoint_hint: str | None = None, headless: bool = False
) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        seen_requests: list[dict[str, Any]] = []

        def on_request(request: Request) -> None:
            seen_requests.append(
                {
                    "url": request.url,
                    "method": request.method,
                    "headers": _pick_headers(request.headers),
                    "path": _path_from_url(request.url),
                }
            )

        page.on("request", on_request)
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(2_500)

        cookies_list = context.cookies()
        cookies = {c["name"]: c["value"] for c in cookies_list}
        user_agent = context._impl_obj._options.get("user_agent") or ""  # type: ignore[attr-defined]

        browser.close()

    selected_headers: dict[str, str] = {}
    if endpoint_hint:
        for req in seen_requests:
            if (
                endpoint_hint.lower() in (req.get("path") or "").lower()
                or endpoint_hint.lower() in (req.get("url") or "").lower()
            ):
                selected_headers = req.get("headers", {})
                break

    return {
        "cookies": cookies,
        "headers": selected_headers,
        "user_agent": user_agent,
        "seen_requests": seen_requests,
    }


def _capture(
    playwright: Playwright,
    url: str,
    timeout_seconds: int,
    headless: bool,
    events: list[ProbeEvent],
) -> None:
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()
    page = context.new_page()

    def on_request(request: Request) -> None:
        if request.resource_type not in {"xhr", "fetch"}:
            return
        event = ProbeEvent(
            kind="http_request",
            timestamp=now_iso(),
            method=request.method,
            url=request.url,
            path=_path_from_url(request.url),
            resource_type=request.resource_type,
            request_headers=_pick_headers(request.headers),
            request_body_preview=truncate(request.post_data),
        )
        events.append(event)

    def on_response(response: Response) -> None:
        request = response.request
        if request.resource_type not in {"xhr", "fetch"}:
            return

        text_preview: str | None
        try:
            text_preview = truncate(response.text())
        except Exception:
            text_preview = "<unavailable>"

        content_type = response.headers.get("content-type", "")
        event = ProbeEvent(
            kind="http_response",
            timestamp=now_iso(),
            method=request.method,
            url=request.url,
            path=_path_from_url(request.url),
            resource_type=request.resource_type,
            status=response.status,
            request_headers=_pick_headers(request.headers),
            response_headers=_pick_headers(response.headers),
            request_body_preview=truncate(request.post_data),
            response_body_preview=text_preview,
            transport=_detect_transport(content_type, request.url),
        )
        events.append(event)

    def on_websocket(ws: WebSocket) -> None:
        open_event = ProbeEvent(
            kind="ws_open",
            timestamp=now_iso(),
            url=ws.url,
            path=_path_from_url(ws.url),
            resource_type="websocket",
            transport="websocket",
        )
        events.append(open_event)

        def on_sent(payload: bytes | str) -> None:
            normalized_payload = (
                payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
            )
            events.append(
                ProbeEvent(
                    kind="ws_send",
                    timestamp=now_iso(),
                    url=ws.url,
                    path=_path_from_url(ws.url),
                    resource_type="websocket",
                    message=truncate(normalized_payload),
                    transport="websocket",
                )
            )

        def on_recv(payload: bytes | str) -> None:
            normalized_payload = (
                payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else payload
            )
            events.append(
                ProbeEvent(
                    kind="ws_recv",
                    timestamp=now_iso(),
                    url=ws.url,
                    path=_path_from_url(ws.url),
                    resource_type="websocket",
                    message=truncate(normalized_payload),
                    transport="websocket",
                )
            )

        ws.on("framesent", on_sent)
        ws.on("framereceived", on_recv)

    page.on("request", on_request)
    page.on("response", on_response)
    page.on("websocket", on_websocket)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(max(timeout_seconds, 1) * 1000)
    finally:
        context.close()
        browser.close()


def _filter_events(events: list[ProbeEvent], contains: str | None) -> list[ProbeEvent]:
    if not contains:
        return events
    needle = contains.lower()

    def include(event: ProbeEvent) -> bool:
        hay = " ".join(
            [
                event.kind,
                event.method or "",
                event.url or "",
                event.path or "",
                event.message or "",
                event.request_body_preview or "",
                event.response_body_preview or "",
            ]
        ).lower()
        return needle in hay

    return [event for event in events if include(event)]
