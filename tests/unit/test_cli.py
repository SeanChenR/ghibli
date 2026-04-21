from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ghibli.cli import app


@pytest.fixture
def runner():
    return CliRunner()


# --- 1.1: --version flag ---

def test_version_flag(runner):
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "ghibli" in result.output
    assert "0.1.0" in result.output


# --- 1.2: --list-sessions empty ---

def test_list_sessions_empty(runner):
    with patch("ghibli.sessions.list_all_sessions", return_value=[]):
        result = runner.invoke(app, ["--list-sessions"])
    assert result.exit_code == 0
    assert "No sessions found" in result.output


# --- 1.3: --json flag ---

def test_json_flag_defaults_false(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        result = runner.invoke(app, [], input="\n")
    assert result.exit_code == 0


def test_json_flag_true_when_passed(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        result = runner.invoke(app, ["--json"], input="\n")
    assert result.exit_code == 0


# --- 1.4: empty line / EOF graceful exit ---

def test_empty_line_exits_gracefully(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        result = runner.invoke(app, [], input="\n")
    assert result.exit_code == 0
    assert "Bye" in result.output


def test_eof_exits_gracefully(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        result = runner.invoke(app, [], input="")
    assert result.exit_code == 0


# --- 1.5: unknown session ID rejected ---

def test_unknown_session_id_rejected(runner):
    with patch("ghibli.sessions.get_session", return_value=None):
        result = runner.invoke(app, ["--session", "nonexistent-id-xyz"])
    assert result.exit_code == 1
    assert "not found" in result.output
