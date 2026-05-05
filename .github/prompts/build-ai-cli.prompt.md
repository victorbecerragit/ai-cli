---
mode: ask
description: Build or refactor a Python CLI chat client from a browser-discovered AI endpoint
---

Create or refactor this repository into a reusable Python CLI chat client for an AI demo or browser-visible AI API.

## Context

I have identified or partially identified an AI endpoint from browser-visible traffic.

Project goal:
- Build a local CLI that can send prompts directly to an AI endpoint from the terminal.
- Keep a browser-based probe mode for discovery and debugging.
- Support one-shot prompts and an interactive chat mode.
- Keep the project educational, transparent, and easy to adapt to other AI demos.

Project-specific inputs:
- Base URL: `${input:base_url:https://example.com}`
- Endpoint path: `${input:endpoint:/completion}`
- Profile name: `${input:profile_name:demo}`
- Existing files or notes to inspect first: `${input:extra_context:README.md, netpeek.py, ai-cli-run.json}`

Before writing code:
1. Inspect the current repository structure.
2. Reuse existing code when practical.
3. Preserve working behavior.
4. Prefer incremental refactoring over a full rewrite unless the current code is too tangled.

## Target outcome

Implement a clean first version of a real CLI with these capabilities:
- Probe mode: inspect browser traffic and detect likely AI endpoints
- Ask mode: send a single prompt directly to the discovered endpoint
- Chat mode: run an interactive terminal REPL
- Bootstrap mode: use Playwright once to establish browser session state, then switch to direct HTTP calls
- Profile system: allow saving per-demo API settings for reuse

## Tech stack

Use:
- Python 3.11+
- Typer preferred for CLI commands, argparse acceptable if already used and cleaner
- Rich for terminal output
- Playwright for browser probing/bootstrap
- requests or httpx for direct HTTP calls

Prefer:
- small modules
- readable functions
- dataclasses or pydantic models for structured config/results
- clear comments where behavior is non-obvious

## Files to create or refactor

Please create or refactor toward this structure when appropriate:

- `cli.py`
- `browser_probe.py`
- `api_client.py`
- `chat_ui.py`
- `models.py`
- `utils.py`
- `profiles.json` or `profiles.yaml`
- `requirements.txt`
- `README.md`

If the repository already has equivalent files, improve them instead of duplicating logic.

## CLI design

Implement commands like:

- `python cli.py probe <url>`
- `python cli.py ask --base-url <url> --endpoint ${input:endpoint:/completion} --prompt "Hello"`
- `python cli.py chat --base-url <url> --endpoint ${input:endpoint:/completion}`
- `python cli.py bootstrap-chat <url> --endpoint ${input:endpoint:/completion}`
- `python cli.py ask --profile ${input:profile_name:demo} --prompt "Hello"`

If Typer is used, keep the CLI intuitive and self-documenting.

## Functional requirements

### 1. Probe mode
Implement or preserve a Playwright-based mode that:
- opens a user-provided URL
- captures network requests and responses
- highlights likely AI endpoints such as `/completion`, `/chat`, `/api/chat`, `/generate`, `/inference`
- logs:
  - method
  - full URL
  - path
  - request headers
  - request payload preview
  - response status
  - response content-type
  - detected transport type (json, sse, websocket, text)

Save captured results to JSON.

### 2. Direct API mode
Implement a reusable API client that supports:
- base URL
- endpoint path
- HTTP method, default POST
- JSON payload template
- custom headers
- cookies
- timeout
- optional streaming support if the endpoint behaves like SSE or chunked text

Start with a configurable payload builder and support common prompt shapes like:
- `{ "prompt": "<user text>" }`
- `{ "message": "<user text>" }`
- `{ "input": "<user text>" }`
- `{ "query": "<user text>" }`

Make this easy to adapt in one place.

### 3. Response parsing
Implement helpers to extract assistant text from common response types:
- JSON response bodies
- text/plain
- SSE-like streamed events
- chunked text

Try common field names such as:
- `text`
- `response`
- `answer`
- `content`
- `message`

If a structured extraction fails, display a safe raw preview.

### 4. Bootstrap mode
Support a mode that:
- opens the site in Playwright
- waits for initial session setup
- extracts cookies from browser context
- optionally reuses useful request headers seen during probe mode
- then performs direct API requests using that session state

Keep this basic and transparent.

### 5. Interactive chat mode
Implement a terminal REPL that:
- accepts repeated prompts
- prints formatted assistant replies
- keeps chat history in memory
- shows timing/status/debug info when useful

Support commands like:
- `/exit`
- `/quit`
- `/clear`
- `/debug`
- `/save <file>`

Optional:
- save transcript as JSON or Markdown

### 6. Profiles
Add a simple profile format in `profiles.json` or `profiles.yaml`.

Each profile should support:
- `base_url`
- `endpoint`
- `method`
- `payload_template`
- `headers`
- `response_text_paths`

Include one example profile using:
- base URL from CLI input or profile
- endpoint `${input:endpoint:/completion}`
- profile name `${input:profile_name:demo}`

### 7. Output UX
Use Rich for:
- colored status lines
- readable errors
- tables for debug information
- panels for assistant responses

If response text looks like Markdown, render it nicely where practical.

## Safety constraints

Keep the implementation educational and transparent.

Do not add:
- stealth plugins
- CAPTCHA bypass
- anti-bot evasion
- auth bypass
- rate-limit bypass
- hidden fingerprinting logic
- anything intended for covert use

Only work with browser-visible traffic and ordinary HTTP behavior.

## Implementation guidance

- Reuse existing repository code where possible.
- Refactor into small units instead of making one large file.
- Keep direct API logic separate from Playwright logic.
- Add helper functions for:
  - payload generation
  - header/cookie merging
  - response text extraction
  - transcript saving
  - endpoint normalization
- Make the design extensible so I can adapt it later to other AI demos.

## README requirements

Update or create `README.md` with:
- installation steps
- dependency installation
- Playwright installation step
- examples for `probe`, `ask`, `chat`, and `bootstrap-chat`
- explanation of browser mode vs direct API mode
- explanation of profiles
- troubleshooting tips for:
  - 401
  - 403
  - missing cookies
  - unexpected payload shape
  - empty responses
  - streaming issues

## Work style

When implementing:
1. First inspect the current repo and summarize what should be reused.
2. Then propose the file layout you will create/update.
3. Then generate the code.
4. Keep the first version working and simple.
5. Prefer practical code over overengineering.

Use the current workspace as the source of truth, especially:
${input:extra_context:README.md, netpeek.py, ai-cli-run.json}