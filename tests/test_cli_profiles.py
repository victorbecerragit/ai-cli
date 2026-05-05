"""Behavioral tests for the `profiles` sub-commands.

Each test creates a fresh ``profiles.json`` by running inside
``runner.isolated_filesystem()``, which changes the working directory to a
temporary folder.  Because ``PROFILES_PATH = Path("profiles.json")`` is a
*relative* path, the CLI ends up writing to that temp folder – giving us full
isolation with no monkey-patching needed.
"""

from __future__ import annotations

from typer.testing import CliRunner

from ai_cli.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _add(name: str, base_url: str = "https://example.com") -> None:
    """Invoke `profiles add` with required args, assert success."""
    result = runner.invoke(app, ["profiles", "add", name, "--base-url", base_url])
    assert result.exit_code == 0, f"profiles add failed:\n{result.output}"


# ---------------------------------------------------------------------------
# `profiles add`
# ---------------------------------------------------------------------------

def test_profiles_add_creates_profile() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            ["profiles", "add", "myprofile", "--base-url", "https://api.example.com"],
        )
        assert result.exit_code == 0
        assert "Added profile: myprofile" in result.output


def test_profiles_add_duplicate_fails() -> None:
    with runner.isolated_filesystem():
        _add("dup")
        result = runner.invoke(
            app,
            ["profiles", "add", "dup", "--base-url", "https://api.example.com"],
        )
        # The CLI should propagate the ValueError raised by profile_manager
        assert result.exit_code != 0


def test_profiles_add_shows_in_list() -> None:
    with runner.isolated_filesystem():
        _add("listed")
        result = runner.invoke(app, ["profiles", "list"])
        assert result.exit_code == 0
        assert "listed" in result.output


def test_profiles_add_custom_options() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            [
                "profiles",
                "add",
                "full",
                "--base-url",
                "https://api.example.com",
                "--endpoint",
                "/v1/chat",
                "--timeout",
                "30",
                "--notes",
                "test note",
            ],
        )
        assert result.exit_code == 0
        # Verify the profile was written by reading it back
        show = runner.invoke(app, ["profiles", "show", "full"])
        assert show.exit_code == 0
        assert "v1/chat" in show.output or "full" in show.output


# ---------------------------------------------------------------------------
# `profiles show`
# ---------------------------------------------------------------------------

def test_profiles_show_existing() -> None:
    with runner.isolated_filesystem():
        _add("visible")
        result = runner.invoke(app, ["profiles", "show", "visible"])
        assert result.exit_code == 0
        assert "visible" in result.output


def test_profiles_show_missing_profile_exits_nonzero() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["profiles", "show", "ghost"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# `profiles update`
# ---------------------------------------------------------------------------

def test_profiles_update_changes_timeout() -> None:
    with runner.isolated_filesystem():
        _add("editable")
        result = runner.invoke(
            app,
            ["profiles", "update", "editable", "--timeout", "120"],
        )
        assert result.exit_code == 0
        assert "Updated profile: editable" in result.output

        # Verify the change persisted
        show = runner.invoke(app, ["profiles", "show", "editable"])
        assert "120" in show.output


def test_profiles_update_missing_profile_exits_nonzero() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(
            app,
            ["profiles", "update", "ghost", "--timeout", "99"],
        )
        assert result.exit_code != 0


def test_profiles_update_changes_notes() -> None:
    with runner.isolated_filesystem():
        _add("noted")
        result = runner.invoke(
            app,
            ["profiles", "update", "noted", "--notes", "new note"],
        )
        assert result.exit_code == 0
        show = runner.invoke(app, ["profiles", "show", "noted"])
        assert "new note" in show.output


# ---------------------------------------------------------------------------
# `profiles delete`
# ---------------------------------------------------------------------------

def test_profiles_delete_removes_profile() -> None:
    with runner.isolated_filesystem():
        _add("todelete")
        result = runner.invoke(app, ["profiles", "delete", "todelete", "--yes"])
        assert result.exit_code == 0
        assert "Deleted profile: todelete" in result.output

        # Should no longer appear in list
        lst = runner.invoke(app, ["profiles", "list"])
        assert "todelete" not in lst.output


def test_profiles_delete_missing_profile_exits_nonzero() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["profiles", "delete", "ghost", "--yes"])
        assert result.exit_code != 0


def test_profiles_delete_cancel_via_no_confirmation() -> None:
    with runner.isolated_filesystem():
        _add("keepme")
        # Supply "n" through stdin when prompted; no --yes flag
        result = runner.invoke(app, ["profiles", "delete", "keepme"], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output

        # Profile should still exist
        lst = runner.invoke(app, ["profiles", "list"])
        assert "keepme" in lst.output


# ---------------------------------------------------------------------------
# `profiles validate`
# ---------------------------------------------------------------------------

def test_profiles_validate_valid_profile_exits_zero() -> None:
    with runner.isolated_filesystem():
        _add("valid")
        result = runner.invoke(app, ["profiles", "validate", "valid"])
        assert result.exit_code == 0


def test_profiles_validate_missing_profile_exits_nonzero() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["profiles", "validate", "ghost"])
        assert result.exit_code != 0
