# ai-cli

A Python CLI for inspecting browser-visible AI network traffic and chatting directly with discovered endpoints — educational, transparent, no magic.

**Modes:** `probe` (Playwright network tab) · `ask` (one-shot HTTP) · `chat` (interactive REPL) · `tui` (rich terminal UI) · `bootstrap-chat` (browser session → direct HTTP)

---

## Quick start

```bash
git clone https://github.com/victorbecerragit/ai-cli.git
cd ai-cli
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # core + dev tools
pip install -e ".[probe]"        # add if you want Playwright probe mode
playwright install chromium      # only needed for probe / bootstrap-chat
```

---

## Try it out — live demo endpoint

A public BitNet demo is available at:

```
https://demo-bitnet-h0h8hcfqeqhrf5gf.canadacentral-01.azurewebsites.net/
```

### 1. Probe — discover what the page sends

```bash
ai-cli probe "https://demo-bitnet-h0h8hcfqeqhrf5gf.canadacentral-01.azurewebsites.net/" \
  --timeout 15 --output probe.json
```

This opens a headful Chromium window, records every XHR/fetch/WebSocket request, and prints the likely AI endpoints with their payloads.

### 2. Ask — one-shot question

```bash
ai-cli ask \
  --base-url "https://demo-bitnet-h0h8hcfqeqhrf5gf.canadacentral-01.azurewebsites.net/" \
  --endpoint "/completion" \
  --prompt "What is 2 + 2?"
```

### 3. Save a profile and reuse it

```bash
ai-cli profiles add demo   # interactive wizard
ai-cli ask --profile demo --prompt "Explain recursion in one sentence"
```

### 4. Interactive chat REPL

```bash
ai-cli chat --profile demo
```

Type `/help` for available commands (`/clear`, `/save`, `/debug`, `/exit`).

### 5. Rich TUI (requires `.[tui]` extra)

```bash
pip install -e ".[tui]"
ai-cli tui --profile demo
```

---

## Installation extras

| Extra | What it adds |
|-------|-------------|
| `.[dev]` | ruff, mypy, pytest |
| `.[probe]` | playwright ≥ 1.45 |
| `.[tui]` | textual |
| `.[all]` | probe + tui |

---

## Development

```bash
ruff check . && ruff format .
mypy src
pytest
```

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
