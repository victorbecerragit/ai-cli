# ai-cli

A Python CLI for inspecting browser-visible AI network traffic and chatting directly with discovered endpoints — educational, transparent, no magic.

**Modes:** `probe` (Playwright network tab) · `ask` (one-shot HTTP) · `chat` (interactive REPL) · `tui` (rich terminal UI) · `bootstrap-chat` (browser session → direct HTTP)

---

# Demo - Short demo showing profile setup and interactive chat.

<a href="https://asciinema.org/a/1020493" target="_blank"><img src="https://asciinema.org/a/1020493.svg" /></a>

## Quick start — users

Install globally with [uv](https://docs.astral.sh/uv/):

```bash
# Base install (ask, chat, profiles only)
uv tool install git+https://github.com/victorbecerragit/ai-cli.git

# With TUI (recommended)
uv tool install "git+https://github.com/victorbecerragit/ai-cli.git[tui]"

# With all features (probe + tui)
uv tool install "git+https://github.com/victorbecerragit/ai-cli.git[all]"

ai-cli --help
```

Install from a local clone (uses your checked-out source):

```bash
git clone https://github.com/victorbecerragit/ai-cli.git
cd ai-cli

# Base install (ask, chat, profiles only)
uv tool install . --force

# If you are actively developing, use editable mode so new code is picked up immediately
uv tool install --editable . --force

# With TUI (recommended)
uv sync --extra all
uv tool install ".[tui]" --force

# With all features (probe + tui)
uv tool install ".[all]" --force

ai-cli --help
```

If `ai-cli` is not found after install, ensure your uv tool bin directory is on `PATH`:

```bash
command -v ai-cli
uv tool dir
```

Or install locally with all optional features:

```bash
uv pip install "ai-cli[all] @ git+https://github.com/victorbecerragit/ai-cli.git"
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

On Linux servers without a display, add `--headless`:

```bash
ai-cli probe "https://demo-bitnet-h0h8hcfqeqhrf5gf.canadacentral-01.azurewebsites.net/" \
  --timeout 15 --output probe.json --headless
```

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

### 5. Rich TUI

```bash
ai-cli tui --profile demo
```

---

## Provider/model aliases

`ai-cli` supports lightweight provider/model resolution using either:
- a saved profile field: `model`
- a CLI override: `--model`

For Google Gemma aliases, the CLI resolves provider settings automatically (base URL, endpoint, method, payload format, response parsing).

Supported Google aliases:
- `google/gemma4` -> `gemma-4-26b-a4b-it`
- `google/gemma-4-26b-a4b-it` -> `gemma-4-26b-a4b-it`
- `google/gemma-4-31b-it` -> `gemma-4-31b-it`

### Add a Google Gemma profile

```bash
ai-cli profiles add google-gemma4 --model google/gemma4
```

### Ask using the profile

```bash
ai-cli ask --profile google-gemma4 --prompt "Hello, Gemma 4!"
```

### Override model on any profile

```bash
ai-cli ask --profile demo --model google/gemma4 --prompt "Summarize this"
```

### API key setup (recommended)

Google requests use your `GEMINI_API_KEY` environment variable.

Fish (persistent):

```bash
set -Ux GEMINI_API_KEY "your-real-key"
```

Bash/Zsh (persistent):

```bash
echo 'export GEMINI_API_KEY="your-real-key"' >> ~/.bashrc
# or ~/.zshrc
```

Then open a new shell and run:

```bash
ai-cli ask --profile google-gemma4 --prompt "Hello"
```

`ai-cli profiles list` shows resolved `base_url`/`endpoint` for alias-backed profiles.

---

## Development setup

```bash
git clone https://github.com/victorbecerragit/ai-cli.git
cd ai-cli
uv sync --group dev        # install project + dev tools (ruff, mypy, pytest)
uv run pytest              # run tests
uv run ruff check .        # lint
uv run ruff format .       # format
uv run mypy src            # type-check
```

To run the CLI from source:

```bash
uv run ai-cli --help
```

---

## Probe / browser setup

`probe` and `bootstrap-chat` require Playwright (not installed by default):

```bash
uv sync --extra probe
uv run playwright install chromium
uv run ai-cli probe "https://example.com" --timeout 10
```

---

## Installation extras

| Extra | What it adds |
|-------|-------------|
| `.[probe]` | playwright ≥ 1.45 |
| `.[tui]` | textual ≥ 0.70 |
| `.[all]` | probe + tui |

---

## Troubleshooting

401 Unauthorized:
- include required auth headers
- run `bootstrap-chat` to refresh session cookies

403 Forbidden:
- site may require a valid browser session context
- retry with `bootstrap-chat` and a saved profile

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
