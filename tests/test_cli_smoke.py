from __future__ import annotations

from typer.testing import CliRunner

from ai_cli.cli import app

runner = CliRunner()


def test_cli_help_renders() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "mini-DevTools" in result.stdout


def test_profiles_list_with_no_profiles_file() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["profiles", "list"])

    assert result.exit_code == 0
    assert "Profiles" in result.stdout
