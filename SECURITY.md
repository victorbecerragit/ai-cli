# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅        |

## Reporting a vulnerability

**Please do not report security vulnerabilities through public GitHub Issues.**

Instead, open a [GitHub Security Advisory](https://github.com/victorbecerragit/ai-cli/security/advisories/new) so the report stays private until a fix is released.

Include:

- A description of the vulnerability and its potential impact
- Steps to reproduce (proof-of-concept if possible)
- Affected versions

You can expect an acknowledgement within **48 hours** and a status update within **7 days**.

## Scope

This project is an **educational CLI tool** for inspecting browser-visible AI network traffic. It does not implement authentication bypass, CAPTCHA evasion, or any anti-bot features by design.

Security issues in scope:

- Command injection via untrusted input (profile names, prompts, headers)
- Credential leakage (API keys logged or written to disk in plaintext)
- Path traversal in profile file handling
- Dependency vulnerabilities (report via the advisory above)

Out of scope (by design):

- The tool connecting to external services — it only sends requests the user explicitly configures
- Playwright browser isolation — use the upstream Playwright security policy for browser-level issues
