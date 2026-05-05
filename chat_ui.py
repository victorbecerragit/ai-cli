from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from api_client import ApiClient
from models import Profile
from utils import now_iso, write_json


console = Console()


def run_chat(
    client: ApiClient,
    profile: Profile,
    debug: bool = False,
) -> None:
    history: list[dict[str, str]] = []
    transcript: list[dict[str, str]] = []
    debug_enabled = debug

    console.print(Panel.fit("Interactive chat started. Commands: /exit /quit /clear /debug /save <file>", title="mini-DevTools"))

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nExiting chat.")
            break

        if not user_input:
            continue

        if user_input in {"/exit", "/quit"}:
            console.print("Exiting chat.")
            break

        if user_input == "/clear":
            history.clear()
            transcript.clear()
            console.print("Conversation history cleared.")
            continue

        if user_input == "/debug":
            debug_enabled = not debug_enabled
            console.print(f"Debug mode: {'on' if debug_enabled else 'off'}")
            continue

        if user_input.startswith("/save "):
            file_name = user_input[6:].strip()
            if not file_name:
                console.print("Usage: /save <file>")
                continue
            payload = {
                "saved_at": now_iso(),
                "profile": profile.name,
                "base_url": profile.base_url,
                "endpoint": profile.endpoint,
                "transcript": transcript,
            }
            write_json(file_name, payload)
            console.print(f"Saved transcript to {file_name}")
            continue

        result = client.ask(user_input, history=history)

        transcript.append({"role": "user", "content": user_input})
        transcript.append({"role": "assistant", "content": result.text})

        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": result.text})

        assistant_output = result.text or "<empty response>"
        console.print(Panel(Markdown(assistant_output), title="assistant", border_style="green"))

        if debug_enabled:
            table = Table(title="debug")
            table.add_column("field")
            table.add_column("value")
            table.add_row("status", str(result.status_code))
            table.add_row("ok", str(result.ok))
            table.add_row("elapsed_ms", str(result.elapsed_ms))
            table.add_row("content_type", str(result.content_type))
            table.add_row("raw_preview", str(result.raw_preview or ""))
            console.print(table)
