# .github/copilot-instructions.md

This repository contains a small educational Python CLI for inspecting browser-visible network activity with Playwright.

Guidelines:
- Prefer Python 3.11+.
- Prefer uv sync, uv run, and uv tool install over manual venv and pip commands in this repository.
- Use Playwright sync API unless async is clearly simpler.
- Keep Chromium headful by default for learning/debugging.
- Focus on XHR, fetch, and WebSocket visibility similar to a basic DevTools Network tab.
- Do not add stealth, CAPTCHA bypass, anti-bot evasion, or auth bypass features.
- Keep implementation simple, readable, and well commented.
- Prefer argparse for CLI flags.
- Export captured traffic to JSON.
- Update README with install and usage examples whenever commands change.
