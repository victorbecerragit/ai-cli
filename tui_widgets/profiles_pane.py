from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import ListItem, ListView, Static

from models import Profile


class ProfilesPane(Vertical):
    def __init__(self) -> None:
        super().__init__(id="sidebar")
        self.profile_names: list[str] = []

    def compose(self) -> ComposeResult:
        yield Static("Profiles", classes="section-title")
        yield ListView(id="profiles-list")
        yield Static(
            "Keys: q quit | ctrl+l clear | ctrl+s save | ctrl+r reload | ctrl+d debug",
            id="sidebar-help",
        )

    def set_profiles(self, profiles: list[Profile], selected_name: str | None = None) -> str | None:
        list_widget = self.query_one("#profiles-list", ListView)
        list_widget.clear()

        self.profile_names = [p.name for p in profiles]
        if not self.profile_names:
            return None

        for profile in profiles:
            subtitle = f"{profile.method} {profile.endpoint}"
            list_widget.append(ListItem(Static(f"{profile.name}\n{subtitle}")))

        name_to_select = selected_name if selected_name in self.profile_names else self.profile_names[0]
        list_widget.index = self.profile_names.index(name_to_select)
        return name_to_select

    def selected_name(self) -> str | None:
        list_widget = self.query_one("#profiles-list", ListView)
        idx = list_widget.index
        if idx is None or idx < 0 or idx >= len(self.profile_names):
            return None
        return self.profile_names[idx]
