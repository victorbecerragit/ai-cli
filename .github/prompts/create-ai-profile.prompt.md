---
mode: ask
description: Create or improve profile management for a Python AI CLI, including add/list/update/validate/test commands
---

Create or refactor profile management for this Python AI CLI project.

## Goal

I want this project to support reusable AI endpoint profiles so I can save and reuse settings for multiple demos or APIs.

Please implement a dedicated CLI command group for profile management and wire it into the existing ask/chat/bootstrap flow.

## Context

Project-specific inputs:
- Profile storage file: `${input:profile_store:profiles.json}`
- Example profile name: `${input:profile_name:bitnet}`
- Example base URL: `${input:base_url:https://example.com}`
- Example endpoint: `${input:endpoint:/completion}`

Before coding:
1. Inspect the current repo structure.
2. Reuse existing config/models code if present.
3. Avoid duplicating profile logic across commands.

## What to build

Add a dedicated command group named `profiles` with commands such as:

- `profiles list`
- `profiles show <name>`
- `profiles add <name>`
- `profiles update <name>`
- `profiles validate <name>`
- `profiles delete <name>`
- `profiles test <name> --prompt "Hello"`

If the current CLI already has subcommands, integrate this cleanly using the existing CLI framework.

## Functional requirements

### 1. Profile model
Create a structured profile model for AI endpoints with fields like:
- `name`
- `base_url`
- `endpoint`
- `method`
- `headers`
- `cookies` (optional)
- `payload_template`
- `prompt_field_candidates`
- `response_text_paths`
- `timeout`
- `notes` (optional)

Use dataclasses or pydantic models if they fit the current codebase.

### 2. Profile storage
Implement a storage layer for profiles using `${input:profile_store:profiles.json}` or YAML if the project already uses YAML.

Requirements:
- load all profiles
- save profiles
- get by name
- overwrite safely on update
- fail clearly on duplicate names
- preserve formatting/readability where possible

If useful, separate this into a storage/helper module.

### 3. Profiles command group
Implement:

#### `profiles list`
- Show all profiles in a readable table
- Include name, base URL, endpoint, method, and timeout

#### `profiles show <name>`
- Print the full resolved profile in readable JSON or a rich table/panel

#### `profiles add <name>`
Support either:
- interactive prompts, or
- flags, or both

Allow setting:
- base URL
- endpoint
- method
- payload template
- headers
- response text paths
- timeout

If interactive mode is easier for first version, prefer that.

#### `profiles update <name>`
- Update one or more fields
- Support partial updates
- Do not silently erase existing values

#### `profiles delete <name>`
- Require confirmation unless `--yes` is passed

#### `profiles validate <name>`
Perform local validation for:
- required fields present
- valid base URL shape
- endpoint path format
- supported HTTP method
- payload template includes a place for user prompt
- headers are a dictionary
- response text paths are a list if present

Validation should return readable errors and warnings.

#### `profiles test <name> --prompt "Hello"`
- Load the profile
- Build a request using the stored config
- Send a safe sample prompt
- Print status code, timing, and parsed response preview
- Reuse the project’s response parsing helpers if they already exist

### 4. Validation design
Add a clear validation function for profiles so it can be reused by:
- `profiles validate`
- `profiles add`
- `profiles update`
- runtime `ask` and `chat`

If useful, support a `--strict` mode.

### 5. Integration with main CLI
Update the main CLI so commands like these work:

- `python cli.py ask --profile ${input:profile_name:bitnet} --prompt "Hi"`
- `python cli.py chat --profile ${input:profile_name:bitnet}`
- `python cli.py bootstrap-chat --profile ${input:profile_name:bitnet}`

Profile values should merge cleanly with explicit CLI flags, where direct flags override profile values.

### 6. Example profile
Create an example profile named `${input:profile_name:bitnet}` with:
- base URL `${input:base_url:https://example.com}`
- endpoint `${input:endpoint:/completion}`
- method `POST`
- a sensible default payload template
- a few prompt field candidates
- a few response text paths

Document clearly where to tweak it if the API expects a different shape.

### 7. Output UX
Use Rich when available for:
- tables
- validation messages
- warnings
- profile display
- test output

Keep output readable in plain terminals too.

### 8. Safety and config hygiene
- Keep profile logic transparent and simple
- Do not store secrets in committed example files unless clearly marked as placeholders
- Prefer environment variables for sensitive tokens if auth is ever needed later
- If the project has sample config files, make them safe to commit

## README updates

Update the README with a section for profile management:
- how profiles work
- where profiles are stored
- command examples for list/add/update/validate/test
- examples of using `--profile` with `ask` and `chat`
- troubleshooting tips for invalid payload templates, missing prompt placeholders, and bad response text paths

## Work style

When implementing:
1. Summarize the current state of the project first.
2. Propose what files you will change.
3. Then generate working code.
4. Keep the first version simple and practical.
5. Reuse existing request/response parsing code if available.

Use the current repository as the source of truth.