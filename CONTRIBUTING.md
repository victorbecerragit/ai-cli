# Contributing to ai-cli

Thanks for taking the time to contribute!

## Development setup

```bash
git clone https://github.com/victorbecerragit/ai-cli.git
cd ai-cli
uv sync --group dev
```

Run the test suite:

```bash
uv run pytest
```

Run linting and type-checking:

```bash
uv run ruff check src tests
uv run mypy src/ai_cli
```

Install in editable mode so the bare `ai-cli` command reflects your changes immediately:

```bash
uv tool install --editable . --force
```

## How to contribute

1. **Fork** the repo and create a branch from `main`.
2. **Write tests** for any new behaviour (tests live in `tests/`).
3. **Make sure CI passes** — all three checks must be green: ruff, mypy, pytest.
4. **Open a pull request** with a clear description of what and why.

## Code style

- Python 3.11+ — use `str | None` union syntax, not `Optional[str]`.
- Keep new dependencies out unless clearly necessary; add them to `pyproject.toml` with a minimum version.
- Prefer the Playwright **sync API**; async is only acceptable when clearly simpler.
- Comments should explain *why*, not *what* — the code shows what.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: short description
fix: short description
docs: short description
refactor: short description
test: short description
chore: short description
```

## Reporting bugs

Open a [GitHub Issue](https://github.com/victorbecerragit/ai-cli/issues) with:
- Steps to reproduce
- Expected vs actual behaviour
- Python version and OS

## Feature requests

Open an issue tagged `enhancement`. Include the use-case — what are you trying to do and why doesn't the current tool serve it?

## Security

Please **do not** open a public issue for security vulnerabilities. See [SECURITY.md](SECURITY.md).
