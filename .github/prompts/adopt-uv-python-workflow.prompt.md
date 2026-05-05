---
mode: ask
description: Refactor a Python project to use uv as the primary workflow for install, sync, run, and tool usage
---

Refactor this Python project to adopt **uv** as the primary workflow tool for development, local execution, and CLI installation.

## Goal

I want this repository to be **uv-first** instead of relying mainly on:
- `python -m venv`
- `pip install -e ...`
- manual activation steps
- scattered install instructions

The project should support a modern Python workflow using:
- `uv sync`
- `uv run`
- `uv tool install`
- optional extras for feature groups
- a clean README with uv-first instructions

## Context

Project inputs:
- Main CLI command name: `${input:cli_name:ai-cli}`
- Main package/module path: `${input:package_name:ai_cli}`
- Existing files to inspect first: `${input:extra_context:pyproject.toml, README.md, cli.py, requirements.txt, Dockerfile}`

Before changing anything:
1. Inspect the current repository structure.
2. Reuse existing packaging if already present.
3. Prefer incremental improvement over unnecessary rewrites.
4. Preserve existing CLI behavior.

## Primary objectives

### 1. Make the project work cleanly with uv
Update or create the necessary project files so that these commands work:

```bash
uv sync
uv run ${input:cli_name:ai-cli} --help
uv run ${input:cli_name:ai-cli} tui
uv run ${input:cli_name:ai-cli} ask --prompt "Hello"
```

If the project has optional features like TUI, probe mode, or dev tooling, ensure they work with `uv` extras.

### 2. Improve dependency structure
Use `pyproject.toml` as the source of truth.

Define clean dependency groups or extras for things like:
- core
- tui
- probe
- dev
- all

Examples of desired workflows:

```bash
uv sync
uv sync --extra tui
uv sync --extra probe
uv sync --extra dev
uv sync --all-extras
```

If the current dependency structure is messy, simplify it while preserving functionality.

### 3. Make local development easier
Replace the old mental model:

- create venv manually
- activate shell
- run pip install commands manually

with a uv-first workflow.

The project should be easy to develop with commands like:

```bash
uv sync --extra dev --extra tui --extra probe
uv run ${input:cli_name:ai-cli} tui --profile bitnet
uv run pytest
```

### 4. Support tool-style installation
If the project is a real CLI app, ensure it can also be installed like a tool:

```bash
uv tool install .
${input:cli_name:ai-cli} --help
```

If there are caveats with local path installs, document them clearly and offer a fallback such as:

```bash
uv tool install git+https://github.com/${input:github_repo:owner/repo}.git
```

### 5. Keep Docker compatible
If the project already has a Dockerfile:
- keep Docker support working
- do not break container builds
- make packaging consistent with the uv-enabled project structure

If useful, suggest minimal Docker adjustments but keep the main focus on local uv workflow.

### 6. Keep existing CLI/TUI behavior
Do not break current commands such as:
- probe
- ask
- chat
- bootstrap-chat
- profile management
- TUI mode

If code movement is needed, keep behavior stable and imports clean.

## Packaging requirements

Please verify or improve these areas:
- `pyproject.toml` exists and is valid
- the project exposes a proper CLI entrypoint
- package imports work when installed, not only when run from the repo root
- static assets such as Textual CSS files are packaged correctly
- optional extras are documented clearly

If the project still uses a flat layout and a `src/` layout would improve reliability, propose and implement it only if the benefit is clear.

## README requirements

Rewrite the install and usage sections to be uv-first.

Include:
- how to install uv
- how to clone the repo
- how to run `uv sync`
- how to run the CLI with `uv run`
- how to install the tool with `uv tool install`
- how to enable optional extras like TUI or probe mode
- how to install Playwright browsers if probe mode is enabled
- a fallback section for pip/pipx users only if necessary

I want the README to clearly separate:
1. quick start for users
2. development setup for contributors
3. optional probe/browser setup

## Preferred end-state examples

I want the project to support workflows like:

### User workflow
```bash
uv tool install git+https://github.com/${input:github_repo:owner/repo}.git
${input:cli_name:ai-cli} --help
```

### Local project workflow
```bash
git clone https://github.com/${input:github_repo:owner/repo}.git
cd ${input:repo_dir:repo}
uv sync --all-extras
uv run ${input:cli_name:ai-cli} tui
```

### Probe mode workflow
```bash
uv sync --extra probe
uv run playwright install chromium
uv run ${input:cli_name:ai-cli} probe https://example.com
```

## Constraints

- Keep the implementation practical and simple.
- Preserve existing functionality.
- Prefer standard uv workflows over custom shell wrappers unless there is a strong reason.
- Do not add unnecessary tooling.
- Avoid overengineering.

## Work style

When implementing:
1. First summarize the current project state.
2. Then list the files you will change.
3. Then apply the changes.
4. Then summarize the new uv-first workflows.
5. Keep the resulting code and documentation easy to maintain.

Use the current repository as the source of truth, especially:
${input:extra_context:pyproject.toml, README.md, cli.py, requirements.txt, Dockerfile}