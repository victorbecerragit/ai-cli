---
mode: ask
description: Upgrade a Python AI CLI into a richer Textual TUI with chat panes, profiles, and debug panels
---

Upgrade this Python AI CLI project from a plain command-line interface into a richer terminal UI using Textual.

## Goal

Turn the current AI CLI into a usable Textual-based TUI for chatting with browser-discovered or profile-based AI endpoints.

The TUI should feel like a lightweight terminal chat application:
- profile-aware
- scrollable chat history
- good keyboard flow
- visible request/debug state
- easy to extend later

This is an upgrade of the existing project, not a full rewrite unless the current structure is too tangled.

## Context

Project-specific inputs:
- Existing CLI entrypoint or main file: `${input:cli_entrypoint:cli.py}`
- Profile store: `${input:profile_store:profiles.json}`
- Default profile name: `${input:profile_name:bitnet}`
- Existing files to inspect first: `${input:extra_context:README.md, cli.py, api_client.py, browser_probe.py, chat_ui.py, profiles.json}`

Before coding:
1. Inspect the current repository structure and summarize reusable modules.
2. Reuse the existing API client, profile logic, and response parsing if possible.
3. Keep the current CLI commands working unless there is a strong reason to refactor them.
4. Add the Textual UI as a new interface layer over the current core logic.

## Primary outcome

Implement a Textual-based TUI that supports:
- selecting a profile
- starting a chat session
- sending prompts
- viewing assistant replies in a scrollable chat area
- showing status/timing/debug information
- optionally saving/exporting the session

## Tech stack

Use:
- Python 3.11+
- Textual
- Rich
- Existing request/profile modules from this repository

Prefer:
- modular design
- event-driven UI
- small reusable widgets
- CSS/TCSS styling for layout and polish
- simple architecture that can later support streaming and multiple tabs

## Files to create or refactor

Please create or refactor toward a structure like this when appropriate:

- `tui_app.py`
- `tui/widgets/chat_message.py`
- `tui/widgets/chat_pane.py`
- `tui/widgets/sidebar.py`
- `tui/widgets/debug_panel.py`
- `tui/screens/profile_picker.py` (optional)
- `tui.tcss`
- update `cli.py`
- update `README.md`

If the repository already contains overlapping files, refactor and reuse instead of duplicating code.

## TUI layout

Design a practical first version with this general layout:

- Top: header with app title, active profile, connection state
- Left sidebar:
  - profiles list
  - session actions
  - optional saved transcript list later
- Center:
  - scrollable chat history
  - user and assistant messages styled differently
  - support long responses and code blocks reasonably well
- Bottom:
  - prompt input
  - send button or Enter-to-send
- Right side or collapsible bottom panel:
  - debug/request panel
  - status, timing, endpoint, method
  - last request/response preview
  - optional raw JSON preview

The layout should remain usable on narrow terminals by collapsing or hiding secondary panels.

## Functional requirements

### 1. Launch command
Add a CLI command such as:

- `python cli.py tui`
- `python cli.py tui --profile ${input:profile_name:bitnet}`

This should launch the Textual UI.

### 2. Profile-aware startup
On startup:
- load available profiles from `${input:profile_store:profiles.json}`
- preselect `${input:profile_name:bitnet}` if present
- show current profile clearly in the UI
- allow switching profiles from the sidebar
- refresh the active connection metadata when the profile changes

### 3. Chat pane
Implement a scrollable chat pane that:
- shows user prompts and assistant replies as separate message widgets
- autoscrolls to the latest message
- handles long text gracefully
- supports markdown-like rendering where practical
- shows timestamps or small metadata per message if useful

If a Rich/Textual markdown widget is practical, use it for assistant responses. If not, implement a clean fallback. Keep code blocks and long lines readable.[web:107][web:56]

### 4. Input behavior
Implement a prompt input area that:
- focuses automatically on startup
- sends on Enter
- supports multiline input if practical, or Shift+Enter if Textual pattern allows
- clears after sending
- disables input while waiting for a response if needed
- shows a loading/busy state while a request is in flight

### 5. Request lifecycle integration
When the user sends a prompt:
- create a user message in the chat pane immediately
- call the existing API client using the active profile
- measure timing
- render the assistant response in the chat pane
- update the debug/status panel with:
  - request URL
  - method
  - status
  - duration
  - selected headers
  - payload preview
  - response preview

If the request fails, show a readable error widget/message in the chat pane and debug panel.

### 6. Debug panel
Implement a debug panel that can show:
- active profile name
- base URL
- endpoint
- HTTP method
- timeout
- last request payload preview
- last response preview
- status code
- timing
- error details if any

Bonus:
- make the debug panel collapsible via keyboard shortcut

### 7. Session actions
Add basic session actions such as:
- clear chat
- save transcript
- reload profiles
- toggle debug panel
- quit app

If practical, support command palette style shortcuts or a footer showing keybindings.

### 8. Keyboard UX
Support useful keyboard shortcuts such as:
- `q` to quit
- `ctrl+l` to clear chat
- `ctrl+s` to save transcript
- `ctrl+r` to reload profiles
- `tab` to move focus
- `esc` to close overlays or panels if used

Use Textual patterns for focus and widget interaction where possible.[web:103][web:115]

### 9. Styling
Use `tui.tcss` or equivalent styling to create a clean, modern terminal layout.

Aim for:
- clear panel separation
- comfortable spacing
- highlighted active profile
- distinct user vs assistant message styling
- readable markdown/code blocks
- sensible colors in both common dark and light terminal themes where possible

Do not overdesign. Keep it elegant and practical.

### 10. Architecture
Keep the TUI as a presentation layer over the existing core modules.

Good separation:
- API client handles network requests
- profile manager handles profile storage/loading/validation
- TUI widgets render state and invoke core services
- transcript saving is reusable outside the TUI

Avoid putting HTTP logic directly inside widgets unless unavoidable.

### 11. Responsive behavior
Design for different terminal sizes:
- on wide terminals, show sidebar + chat + debug panel
- on narrower terminals, hide or collapse debug panel first
- keep chat usable even in small terminals

### 12. Error handling
Handle gracefully:
- no profiles found
- invalid selected profile
- request timeout
- malformed response
- empty response text
- profile reload failure

Show these in a user-friendly way, not as raw stack traces unless debug mode is enabled.

## Optional streaming support

If the existing API client already supports streaming or SSE-like responses:
- render partial assistant output incrementally in the chat pane
- keep implementation simple
- only add this if it fits cleanly into the current codebase

If streaming is too invasive for now, leave a clear extension point.

## README updates

Update `README.md` with:
- how to launch the TUI
- keyboard shortcuts
- how profiles work in the TUI
- screenshots section placeholder or text description
- note on terminal compatibility
- troubleshooting for rendering/layout issues

## Work style

When implementing:
1. First inspect and summarize the existing repository.
2. Then propose the files/components you will create or modify.
3. Then generate working code.
4. Keep the first version simple and reliable.
5. Prefer practical functionality over too many widgets.

Use the current repository as the source of truth, especially:
${input:extra_context:README.md, cli.py, api_client.py, browser_probe.py, chat_ui.py, profiles.json}