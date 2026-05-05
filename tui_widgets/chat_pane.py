from __future__ import annotations

from rich.markdown import Markdown
from rich.panel import Panel
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, RichLog


class ChatPane(Vertical):
    def __init__(self) -> None:
        super().__init__(id="chat-column")

    def compose(self) -> ComposeResult:
        yield RichLog(id="chat-log", auto_scroll=True, wrap=True, markup=False)
        yield Input(placeholder="Type a prompt and press Enter...", id="prompt-input")

    def clear_chat(self) -> None:
        self.query_one("#chat-log", RichLog).clear()

    def focus_input(self) -> None:
        self.query_one("#prompt-input", Input).focus()

    def set_input_disabled(self, disabled: bool) -> None:
        self.query_one("#prompt-input", Input).disabled = disabled

    def clear_input(self) -> None:
        self.query_one("#prompt-input", Input).value = ""

    def append_user(self, text: str) -> None:
        self.query_one("#chat-log", RichLog).write(Panel(text, title="you", border_style="cyan"))

    def append_assistant(self, text: str) -> None:
        log = self.query_one("#chat-log", RichLog)
        if text.strip().startswith("#") or "```" in text:
            log.write(Panel(Markdown(text), title="assistant", border_style="green"))
        else:
            log.write(Panel(text, title="assistant", border_style="green"))

    def append_system(self, text: str) -> None:
        self.query_one("#chat-log", RichLog).write(Panel(text, title="system", border_style="yellow"))

    def append_error(self, text: str) -> None:
        self.query_one("#chat-log", RichLog).write(Panel(text, title="error", border_style="red"))
