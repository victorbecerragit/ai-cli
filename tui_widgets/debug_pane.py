from __future__ import annotations

import json

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Static


class DebugPane(Vertical):
    def __init__(self) -> None:
        super().__init__(id="debug-column")

    def compose(self) -> ComposeResult:
        yield Static("Debug", classes="section-title")
        yield Static(id="debug-content")

    def set_data(self, payload: dict[str, object]) -> None:
        self.query_one("#debug-content", Static).update(json.dumps(payload, indent=2, ensure_ascii=True))

    def set_visible(self, visible: bool) -> None:
        self.display = visible
