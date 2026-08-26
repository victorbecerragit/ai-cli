from __future__ import annotations

import json
import os
from typing import Any, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .api_client import ApiClient
from .models import Profile
from .profile_manager import (
    PROFILES_PATH,
    add_profile,
    delete_profile,
    get_profile,
    load_profiles,
    parse_payload_template,
    profile_from_dict,
    profile_to_storage,
    update_profile,
    validate_profile,
)
from .utils import parse_cookie_pairs, parse_header_pairs

app = typer.Typer(help="mini-DevTools: Browser probe + direct CLI chat client")
profiles_app = typer.Typer(help="Manage reusable AI endpoint profiles")
app.add_typer(profiles_app, name="profiles")

console = Console()


@app.command("tui")
def cmd_tui(
    profile: Optional[str] = typer.Option(None, help="Profile name to preselect"),
    debug: bool = typer.Option(True, help="Show debug panel on startup"),
) -> None:
    from .tui_app import AiCliTui

    AiCliTui(start_profile=profile, debug_visible=debug).run()


@app.command("serve-copilot")
def cmd_serve_copilot(
    host: str = typer.Option("127.0.0.1", help="Host to bind the server to"),
    port: int = typer.Option(8000, help="Port to bind the server to"),
    reload: bool = typer.Option(False, "--reload", help="Enable auto-reload for development"),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", help="API Key required to access this bridge"
    ),
) -> None:
    """
    Start the GitHub Copilot extension bridge server.
    """
    try:
        import uvicorn

        from .copilot_extension import app as fastapi_app
    except ImportError:
        console.print(
            "[bold red]Error:[/bold red] Missing dependencies for the Copilot server.\n"
            "Please install with the [bold cyan]serve[/bold cyan] extra:\n\n"
            '  [yellow]uv tool install ".[serve]" --force[/yellow]'
        )
        raise typer.Exit(code=1)

    if api_key:
        os.environ["AI_CLI_API_KEY"] = api_key

    console.print(
        Panel(
            f"Starting Copilot Extension server on [bold cyan]http://{host}:{port}[/bold cyan]",
            title="Copilot Bridge",
        )
    )
    if reload:
        uvicorn.run("ai_cli.copilot_extension:app", host=host, port=port, reload=True)
    else:
        uvicorn.run(fastapi_app, host=host, port=port)


def _merge_profile_with_overrides(
    profile_name: Optional[str],
    base_url: Optional[str],
    endpoint: Optional[str],
    method: Optional[str],
    headers: dict[str, str],
    cookies: dict[str, str],
    timeout: Optional[int],
    stream: Optional[bool],
) -> Profile:
    base: Profile
    if profile_name:
        loaded = get_profile(profile_name)
        if not loaded:
            raise typer.BadParameter(f"Profile '{profile_name}' not found")
        base = loaded
    else:
        if not base_url:
            raise typer.BadParameter("Provide --base-url or --profile")
        base = Profile(name="ad-hoc", base_url=base_url)

    return Profile(
        name=profile_name or base.name,
        base_url=base_url or base.base_url,
        endpoint=endpoint or base.endpoint,
        method=(method or base.method).upper(),
        payload_template=base.payload_template,
        headers={**base.headers, **headers},
        cookies={**base.cookies, **cookies},
        prompt_field_candidates=base.prompt_field_candidates,
        response_text_paths=base.response_text_paths,
        timeout=timeout or base.timeout,
        notes=base.notes,
        stream=base.stream if stream is None else stream,
        model=base.model,
    )


def _render_validation(name: str, errors: list[str], warnings: list[str]) -> None:
    if errors:
        table = Table(title=f"Profile '{name}' validation errors")
        table.add_column("level")
        table.add_column("message")
        for err in errors:
            table.add_row("error", err)
        for warn in warnings:
            table.add_row("warning", warn)
        console.print(table)
        return

    table = Table(title=f"Profile '{name}' validation")
    table.add_column("level")
    table.add_column("message")
    table.add_row("ok", "Profile is valid")
    for warn in warnings:
        table.add_row("warning", warn)
    console.print(table)


@app.command("probe")
def cmd_probe(
    url: str,
    timeout: int = typer.Option(12, help="Capture duration in seconds"),
    contains: Optional[str] = typer.Option(None, help="Optional text filter"),
    output: str = typer.Option("probe-output.json", help="JSON output path"),
    headless: bool = typer.Option(False, help="Run Chromium headless"),
) -> None:
    from .browser_probe import probe_url

    payload = probe_url(
        url=url, timeout_seconds=timeout, headless=headless, contains=contains, output=output
    )

    endpoints = payload.get("likely_endpoints", [])
    table = Table(title="Likely AI Endpoints")
    table.add_column("method")
    table.add_column("path")
    table.add_column("transport")
    table.add_column("url")

    for endpoint_row in endpoints:
        table.add_row(
            str(endpoint_row.get("method", "")),
            str(endpoint_row.get("path", "")),
            str(endpoint_row.get("transport", "")),
            str(endpoint_row.get("url", "")),
        )

    console.print(table)
    console.print(f"Saved probe capture to {output}")


@app.command("ask")
def cmd_ask(
    prompt: str = typer.Option(..., "--prompt", "-p", help="Prompt text"),
    profile: Optional[str] = typer.Option(None, help="Saved profile name"),
    base_url: Optional[str] = typer.Option(None, help="Base URL override"),
    endpoint: Optional[str] = typer.Option(None, help="Endpoint path override"),
    method: Optional[str] = typer.Option(None, help="HTTP method override"),
    header: list[str] = typer.Option([], help="Header pair: Key:Value"),
    cookie: list[str] = typer.Option([], help="Cookie pair: key=value"),
    timeout: Optional[int] = typer.Option(None, help="Request timeout seconds override"),
    stream: Optional[bool] = typer.Option(None, help="Enable/disable streaming support"),
    model: Optional[str] = typer.Option(None, help="Model alias override (e.g. google/gemma4)"),
) -> None:
    parsed_headers = parse_header_pairs(header)
    parsed_cookies = parse_cookie_pairs(cookie)

    resolved = _merge_profile_with_overrides(
        profile_name=profile,
        base_url=base_url,
        endpoint=endpoint,
        method=method,
        headers=parsed_headers,
        cookies=parsed_cookies,
        timeout=timeout,
        stream=stream,
    )

    errors, warnings = validate_profile(resolved)
    if errors:
        _render_validation(resolved.name, errors, warnings)
        raise typer.Exit(code=1)

    client = ApiClient(resolved, model_override=model)
    result = client.ask(prompt)

    panel_title = f"assistant (status={result.status_code}, {result.elapsed_ms}ms)"
    style = "green" if result.ok else "red"
    console.print(Panel(result.text, title=panel_title, border_style=style))

    if not result.ok:
        raise typer.Exit(code=1)


@app.command("chat")
def cmd_chat(
    profile: Optional[str] = typer.Option(None, help="Saved profile name"),
    base_url: Optional[str] = typer.Option(None, help="Base URL override"),
    endpoint: Optional[str] = typer.Option(None, help="Endpoint path override"),
    method: Optional[str] = typer.Option(None, help="HTTP method override"),
    header: list[str] = typer.Option([], help="Header pair: Key:Value"),
    cookie: list[str] = typer.Option([], help="Cookie pair: key=value"),
    timeout: Optional[int] = typer.Option(None, help="Request timeout seconds override"),
    stream: Optional[bool] = typer.Option(None, help="Enable/disable streaming support"),
    debug: bool = typer.Option(False, help="Start chat with debug output enabled"),
    model: Optional[str] = typer.Option(None, help="Model alias override (e.g. google/gemma4)"),
) -> None:
    from .chat_ui import run_chat

    parsed_headers = parse_header_pairs(header)
    parsed_cookies = parse_cookie_pairs(cookie)

    resolved = _merge_profile_with_overrides(
        profile_name=profile,
        base_url=base_url,
        endpoint=endpoint,
        method=method,
        headers=parsed_headers,
        cookies=parsed_cookies,
        timeout=timeout,
        stream=stream,
    )

    errors, warnings = validate_profile(resolved)
    if errors:
        _render_validation(resolved.name, errors, warnings)
        raise typer.Exit(code=1)

    client = ApiClient(resolved, model_override=model)
    run_chat(client, resolved, debug=debug)


@app.command("bootstrap-chat")
def cmd_bootstrap_chat(
    url: str,
    endpoint: str = typer.Option("/completion", help="Endpoint path"),
    profile: Optional[str] = typer.Option(None, help="Use this profile name if saved"),
    save_profile_name: Optional[str] = typer.Option(
        None, "--save-profile", help="Save bootstrap profile under this name"
    ),
    timeout: int = typer.Option(60, help="Request timeout seconds"),
    headless: bool = typer.Option(False, help="Run browser headless"),
) -> None:
    from .browser_probe import bootstrap_session
    from .chat_ui import run_chat

    console.print("Bootstrapping browser session...")
    session = bootstrap_session(url=url, endpoint_hint=endpoint, headless=headless)

    auto_headers = {
        k: v
        for k, v in session.get("headers", {}).items()
        if k.lower()
        in {"origin", "referer", "user-agent", "authorization", "content-type", "accept"}
    }

    resolved = _merge_profile_with_overrides(
        profile_name=profile,
        base_url=url,
        endpoint=endpoint,
        method="POST",
        headers=auto_headers,
        cookies=session.get("cookies", {}),
        timeout=timeout,
        stream=True,
    )

    if save_profile_name:
        to_store = Profile(
            name=save_profile_name,
            base_url=resolved.base_url,
            endpoint=resolved.endpoint,
            method=resolved.method,
            payload_template={"messages": "{{messages}}"},
            headers=resolved.headers,
            cookies=resolved.cookies,
            prompt_field_candidates=["messages", "prompt", "message", "input", "query"],
            response_text_paths=["answer", "response", "content", "choices.0.message.content"],
            timeout=timeout,
            notes="Created by bootstrap-chat",
            stream=True,
        )
        errors, warnings = validate_profile(to_store)
        if errors:
            _render_validation(save_profile_name, errors, warnings)
            raise typer.Exit(code=1)

        existing = get_profile(save_profile_name)
        if existing:
            update_profile(
                save_profile_name,
                {
                    "base_url": to_store.base_url,
                    "endpoint": to_store.endpoint,
                    "method": to_store.method,
                    "payload_template": to_store.payload_template,
                    "headers": to_store.headers,
                    "cookies": to_store.cookies,
                    "prompt_field_candidates": to_store.prompt_field_candidates,
                    "response_text_paths": to_store.response_text_paths,
                    "timeout": to_store.timeout,
                    "notes": to_store.notes,
                    "stream": to_store.stream,
                },
            )
            console.print(f"Updated profile: {save_profile_name}")
        else:
            add_profile(to_store)
            console.print(f"Saved profile: {save_profile_name}")

    client = ApiClient(resolved)
    console.print(
        Panel(
            "Bootstrap complete. Starting interactive chat.",
            title="bootstrap-chat",
            border_style="cyan",
        )
    )
    run_chat(client, resolved, debug=False)


@profiles_app.command("list")
def profiles_list() -> None:
    from .provider_registry import resolve_model_alias as _resolve

    profiles = load_profiles()

    table = Table(title=f"Profiles ({PROFILES_PATH})")
    table.add_column("name")
    table.add_column("base_url")
    table.add_column("endpoint")
    table.add_column("method")
    table.add_column("timeout")
    table.add_column("model")

    for name in sorted(profiles.keys()):
        profile = profile_from_dict(name, profiles[name])
        selected_model = profile.model or profile.name
        spec = _resolve(selected_model)
        display_base_url = spec.base_url if spec else profile.base_url
        display_endpoint = spec.endpoint if spec else profile.endpoint
        model_label = profile.model or ""
        table.add_row(
            name,
            display_base_url,
            display_endpoint,
            profile.method,
            str(profile.timeout),
            model_label,
        )

    console.print(table)


@profiles_app.command("show")
def profiles_show(name: str) -> None:
    profile = get_profile(name)
    if not profile:
        raise typer.BadParameter(f"Profile '{name}' not found")
    console.print(
        Panel(
            json.dumps(
                {
                    "name": profile.name,
                    **{k: v for k, v in profile.__dict__.items() if k != "name"},
                },
                indent=2,
            ),
            title=f"profile: {name}",
        )
    )


@profiles_app.command("add")
def profiles_add(
    name: str,
    base_url: Optional[str] = typer.Option(None, help="Base URL"),
    endpoint: str = typer.Option("/completion", help="Endpoint path"),
    method: str = typer.Option("POST", help="HTTP method"),
    timeout: int = typer.Option(60, help="Timeout in seconds"),
    header: list[str] = typer.Option([], help="Header pair: Key:Value"),
    cookie: list[str] = typer.Option([], help="Cookie pair: key=value"),
    response_path: list[str] = typer.Option([], help="Response text path, repeatable"),
    prompt_field: list[str] = typer.Option([], help="Prompt field candidate, repeatable"),
    payload_template: Optional[str] = typer.Option(None, help="Payload template JSON string"),
    notes: Optional[str] = typer.Option(None, help="Optional notes"),
    stream: bool = typer.Option(True, help="Enable streaming support"),
    model: Optional[str] = typer.Option(None, help="Model alias (e.g. google/gemma4)"),
    overwrite: bool = typer.Option(False, "--overwrite", "-f", help="Overwrite existing profile"),
) -> None:
    from .provider_registry import resolve_model_alias as _resolve

    if not overwrite and get_profile(name):
        console.print(
            f"[bold red]Error:[/bold red] Profile '{name}' already exists. Use [yellow]--overwrite[/yellow] to replace it or [yellow]profiles update[/yellow] to modify it."
        )
        raise typer.Exit(code=1)

    is_registered = _resolve(model or name) is not None
    actual_base_url = base_url or ("" if is_registered else typer.prompt("Base URL"))
    parsed_headers = parse_header_pairs(header)
    parsed_cookies = parse_cookie_pairs(cookie)

    if payload_template:
        payload = parse_payload_template(payload_template)
    else:
        payload = {
            "messages": "{{messages}}",
            "userId": "cli_user",
            "chatId": "cli_chat",
            "device": "cpu",
        }

    profile = Profile(
        name=name,
        base_url=actual_base_url,
        endpoint=endpoint,
        method=method.upper(),
        payload_template=payload,
        headers=parsed_headers,
        cookies=parsed_cookies,
        prompt_field_candidates=prompt_field or ["messages", "prompt", "message", "input", "query"],
        response_text_paths=response_path
        or ["answer", "response", "content", "choices.0.message.content"],
        timeout=timeout,
        notes=notes,
        stream=stream,
        model=model,
    )

    errors, warnings = validate_profile(profile)
    _render_validation(name, errors, warnings)
    if errors:
        raise typer.Exit(code=1)

    if overwrite and get_profile(name):
        update_profile(name, profile_to_storage(profile))
        console.print(f"Updated profile: {name}")
    else:
        add_profile(profile)
        console.print(f"Added profile: {name}")


@profiles_app.command("update")
def profiles_update(
    name: str,
    base_url: Optional[str] = typer.Option(None),
    endpoint: Optional[str] = typer.Option(None),
    method: Optional[str] = typer.Option(None),
    timeout: Optional[int] = typer.Option(None),
    notes: Optional[str] = typer.Option(None),
) -> None:
    updates: dict[str, Any] = {
        "base_url": base_url,
        "endpoint": endpoint,
        "method": method.upper() if method else None,
        "timeout": timeout,
        "notes": notes,
    }

    updated = update_profile(name, updates)
    errors, warnings = validate_profile(updated)
    _render_validation(name, errors, warnings)
    if errors:
        raise typer.Exit(code=1)

    console.print(f"Updated profile: {name}")


@profiles_app.command("delete")
def profiles_delete(
    name: str, yes: bool = typer.Option(False, "--yes", help="Skip confirmation")
) -> None:
    if not yes:
        confirmed = typer.confirm(f"Delete profile '{name}'?")
        if not confirmed:
            console.print("Cancelled")
            raise typer.Exit(code=0)

    delete_profile(name)
    console.print(f"Deleted profile: {name}")


@profiles_app.command("validate")
def profiles_validate(
    name: str, strict: bool = typer.Option(False, help="Enable strict warnings")
) -> None:
    profile = get_profile(name)
    if not profile:
        raise typer.BadParameter(f"Profile '{name}' not found")

    errors, warnings = validate_profile(profile, strict=strict)
    _render_validation(name, errors, warnings)

    if errors:
        raise typer.Exit(code=1)


@profiles_app.command("test")
def profiles_test(
    name: str,
    prompt: str = typer.Option(..., "--prompt", "-p", help="Prompt to send"),
) -> None:
    profile = get_profile(name)
    if not profile:
        raise typer.BadParameter(f"Profile '{name}' not found")

    errors, warnings = validate_profile(profile)
    _render_validation(name, errors, warnings)
    if errors:
        raise typer.Exit(code=1)

    client = ApiClient(profile)
    result = client.ask(prompt)

    table = Table(title=f"Profile test: {name}")
    table.add_column("field")
    table.add_column("value")
    table.add_row("status", str(result.status_code))
    table.add_row("ok", str(result.ok))
    table.add_row("elapsed_ms", str(result.elapsed_ms))
    table.add_row("content_type", str(result.content_type))
    table.add_row("response_preview", result.text)
    console.print(table)

    if not result.ok:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
