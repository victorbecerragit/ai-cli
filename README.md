# mini-DevTools CLI Chat Client

This project is a real Python CLI chat client built from browser-visible AI endpoint discovery.

It supports:
- probe mode with Playwright network inspection
- direct one-shot ask mode over HTTP
- interactive terminal chat mode
- bootstrap mode (browser session setup plus direct HTTP chat)
- reusable profiles in profiles.json

The implementation is educational and transparent.

## Requirements

- Python 3.11+
- Playwright Chromium browser

## Installation

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Install Chromium for Playwright:

```bash
playwright install chromium
```

## Command Overview

```bash
ai-cli --help
```

Main commands:
- ai-cli probe <url>
- ai-cli ask --prompt "..."
- ai-cli chat
- ai-cli bootstrap-chat <url>
- ai-cli tui
- ai-cli profiles list
- ai-cli profiles add <name>
- ai-cli profiles validate <name>
- ai-cli profiles test <name> --prompt "hello"

Backward-compatible entrypoint:
- python netpeek.py ...

If `ai-cli` is not found, activate the virtualenv first:

```bash
source .venv/bin/activate
```

## Probe Mode

Probe browser-visible traffic and save likely AI endpoints:

```bash
ai-cli probe "https://demo-bitnet-h0h8hcfqeqhrf5gf.canadacentral-01.azurewebsites.net/" --timeout 15 --output probe.json
```

Probe output includes:
- HTTP method
- full URL and path
- selected request/response headers
- request payload preview
- response body preview
- transport hint (json, sse, websocket, text)
- likely endpoints matching patterns like /completion, /chat, /api/chat, /generate, /inference

## Ask Mode

Use a saved profile:

```bash
ai-cli ask --profile bitnet --prompt "Hello from CLI"
```

Or specify base URL and endpoint directly:

```bash
ai-cli ask \
  --base-url "https://demo-bitnet-h0h8hcfqeqhrf5gf.canadacentral-01.azurewebsites.net/" \
  --endpoint "/completion" \
  --prompt "Hello from CLI"
```

Optional headers and cookies:

```bash
ai-cli ask \
  --base-url "https://example.com" \
  --endpoint "/completion" \
  --prompt "Hello" \
  --header "Authorization: Bearer TOKEN" \
  --cookie "sessionid=abc123"
```

## Chat Mode

Interactive REPL:

```bash
ai-cli chat --profile bitnet
```

Chat commands:
- /exit or /quit
- /clear
- /debug
- /save transcript.json

## Textual TUI Mode

Launch the richer terminal UI:

```bash
ai-cli tui
```

Launch with a preselected profile:

```bash
ai-cli tui --profile bitnet
```

Layout:
- Left pane: profiles list and quick key hints
- Center pane: scrollable chat history and prompt input
- Right pane: debug panel with profile/request/response metadata

Default keybindings:
- q: quit
- ctrl+l: clear chat
- ctrl+s: save transcript JSON
- ctrl+r: reload profiles
- ctrl+d: toggle debug panel
- tab or esc: focus prompt input

Notes:
- On narrow terminals, the debug panel auto-hides.
- The TUI uses the same profile store and API client as ask/chat commands.
- If there are no profiles, create one first with `ai-cli profiles add <name>`.

## Bootstrap Chat Mode

Use Playwright once to establish session state, then switch to direct HTTP chat:

```bash
ai-cli bootstrap-chat \
  "https://demo-bitnet-h0h8hcfqeqhrf5gf.canadacentral-01.azurewebsites.net/" \
  --endpoint "/completion" \
  --save-profile demo_bootstrap
```

Bootstrap captures:
- browser cookies
- useful request headers (origin, referer, user-agent, etc.)

Then starts interactive chat with that state.

## Profiles

Dedicated profile management commands:

```bash
ai-cli profiles list
ai-cli profiles add bitnet
ai-cli profiles validate bitnet
ai-cli profiles test bitnet --prompt "hello"
ai-cli profiles show bitnet
ai-cli profiles update bitnet --timeout 90
ai-cli profiles delete bitnet --yes
```

Profiles are stored in profiles.json. Example:

```json
{
  "profiles": {
    "demo": {
      "base_url": "https://demo-bitnet-h0h8hcfqeqhrf5gf.canadacentral-01.azurewebsites.net/",
      "endpoint": "/completion",
      "method": "POST",
      "payload_template": {
        "messages": "{{messages}}",
        "userId": "cli_user",
        "chatId": "cli_chat",
        "device": "cpu"
      },
      "headers": {
        "content-type": "application/json"
      },
      "response_text_paths": ["content", "answer", "response", "choices.0.message.content"],
      "stream": true
    }
  }
}
```

Supported profile fields:
- base_url
- endpoint
- method
- payload_template
- headers
- response_text_paths
- stream

## Payload and Response Handling

The client supports common prompt payload shapes through templates and extraction logic.

Prompt templates can include:
- {{prompt}}
- {{messages}}

Response parsing supports:
- JSON fields like text, response, answer, content, message
- nested paths like choices.0.message.content
- SSE streams with data lines and [DONE]
- plain text fallback

## Browser Mode vs Direct API Mode

Browser mode (probe and bootstrap-chat):
- best for discovery and session setup
- useful for debugging what the page actually sends

Direct API mode (ask and chat):
- best for daily CLI usage
- faster and simpler after endpoint details are known

## Troubleshooting

401 Unauthorized:
- include required auth headers
- run bootstrap-chat to refresh session cookies

403 Forbidden:
- site may require valid browser session context
- retry with bootstrap-chat and saved profile

Missing cookies:
- re-run bootstrap-chat
- avoid stale cookie values copied from old runs

Unexpected payload shape:
- adjust payload_template in profiles.json
- compare with probe output request body previews

Empty responses:
- check endpoint, method, and content-type
- enable chat debug with /debug
- update response_text_paths in profile

Streaming issues:
- set stream to false in profile for non-SSE endpoints
- verify response content-type from probe output

TUI rendering/layout issues:
- ensure your terminal supports modern ANSI features
- resize terminal wider than 120 columns for full 3-pane layout
- update dependencies with `pip install -r requirements.txt`

## Safety

This project is for educational inspection and normal HTTP interaction only.

Do not add:
- stealth plugins
- CAPTCHA bypass
- anti-bot evasion
- auth bypass
- hidden fingerprinting logic

Use only on sites and endpoints you are authorized to inspect.
