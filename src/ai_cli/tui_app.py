from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input, ListView

from .tui_controller import TuiController
from .tui_widgets import ChatPane, DebugPane, ProfilesPane


class AiCliTui(App[None]):
    CSS_PATH = "tui.tcss"
    TITLE = "ai-cli"
    SUB_TITLE = "Textual Chat UI"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+l", "clear_chat", "Clear Chat"),
        Binding("ctrl+s", "save_transcript", "Save"),
        Binding("ctrl+r", "reload_profiles", "Reload"),
        Binding("ctrl+d", "toggle_debug", "Toggle Debug"),
        Binding("tab", "focus_input", "Focus Input"),
        Binding("escape", "focus_input", "Focus Input"),
    ]

    def __init__(self, start_profile: str | None = None, debug_visible: bool = True) -> None:
        super().__init__()
        self.debug_visible = debug_visible
        self.controller = TuiController(start_profile=start_profile)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Horizontal(id="layout"):
            yield ProfilesPane()
            yield ChatPane()
            yield DebugPane()

        yield Footer()

    def on_mount(self) -> None:
        self._load_profiles_ui()
        self._apply_debug_visibility()

        self.query_one(ChatPane).append_system("Welcome to ai-cli TUI. Select a profile and start chatting.")

        self.query_one(ChatPane).focus_input()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        chat_pane = self.query_one(ChatPane)

        if not prompt:
            return

        if not self.controller.active_profile_name:
            chat_pane.append_system("No active profile selected. Use the profiles list on the left.")
            chat_pane.clear_input()
            return

        profile = self.controller.active_profile()
        if not profile:
            chat_pane.append_system(f"Profile '{self.controller.active_profile_name}' not found.")
            chat_pane.clear_input()
            return

        chat_pane.set_input_disabled(True)
        chat_pane.clear_input()

        chat_pane.append_user(prompt)
        self.controller.mark_request_in_flight(profile, prompt)
        self._render_debug()

        try:
            result = await asyncio.to_thread(self.controller.ask_sync, profile, prompt)
            chat_pane.append_assistant(result.text)
            self._render_debug()
        except Exception as exc:
            chat_pane.append_error(f"Request failed: {exc}")
            self.controller.mark_exception(profile, exc)
            self._render_debug()
        finally:
            chat_pane.set_input_disabled(False)
            chat_pane.focus_input()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "profiles-list":
            return

        if event.item is None:
            return

        selected_name = self.query_one(ProfilesPane).selected_name()
        if not selected_name:
            return

        profile = self.controller.select_profile(selected_name)
        if profile:
            self.controller.clear_chat_state()
            self._render_debug()
            chat_pane = self.query_one(ChatPane)
            chat_pane.clear_chat()
            chat_pane.append_system(f"Active profile: {selected_name}")

    def action_clear_chat(self) -> None:
        self.controller.clear_chat_state()
        chat_pane = self.query_one(ChatPane)
        chat_pane.clear_chat()
        chat_pane.append_system("Chat cleared.")

    def action_reload_profiles(self) -> None:
        self._load_profiles_ui()
        self.query_one(ChatPane).append_system("Profiles reloaded.")

    def action_save_transcript(self) -> None:
        file_name = self.controller.save_transcript()
        self.query_one(ChatPane).append_system(f"Transcript saved: {file_name}")

    def action_toggle_debug(self) -> None:
        self.debug_visible = not self.debug_visible
        self._apply_debug_visibility()

    def action_focus_input(self) -> None:
        self.query_one(ChatPane).focus_input()

    def _apply_debug_visibility(self) -> None:
        self.query_one(DebugPane).set_visible(self.debug_visible)

    def _load_profiles_ui(self) -> None:
        ordered_profiles, selected_name = self.controller.load_profiles()
        pane = self.query_one(ProfilesPane)

        if not ordered_profiles:
            self._render_debug()
            return

        selected = pane.set_profiles(ordered_profiles, selected_name=selected_name)
        if selected is None:
            return
        self._render_debug()

    def _render_debug(self) -> None:
        self.query_one(DebugPane).set_data(self.controller.last_debug)
