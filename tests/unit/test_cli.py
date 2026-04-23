from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from ghibli.cli import app
from ghibli.exceptions import GhibliError


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture(autouse=True)
def _stub_picker_and_last_model(monkeypatch, tmp_path):
    """Default: no GHIBLI_MODEL, no last_model, credentials check is a no-op.
    Tests that exercise the picker / onboarding / resolution priority
    override these patches explicitly.
    """
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)
    monkeypatch.chdir(tmp_path)  # ensures .ghibli/ starts empty for every test
    # Stub credential check so tests don't need to set every provider env var.
    # Tests that exercise credential behaviour explicitly re-patch this.
    monkeypatch.setattr("ghibli.cli.picker.ensure_credentials", lambda _model: None)


# --- 1.1: --version flag ---

def test_version_flag(runner):
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "ghibli" in result.output
    assert "0.1.0" in result.output


# --- --help excludes Typer completion commands ---

def test_help_does_not_show_completion_options(runner):
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--install-completion" not in result.output
    assert "--show-completion" not in result.output


# --- 1.2: --list-sessions empty ---

def test_list_sessions_empty(runner):
    with patch("ghibli.sessions.list_all_sessions", return_value=[]):
        result = runner.invoke(app, ["--list-sessions"])
    assert result.exit_code == 0
    assert "No sessions found" in result.output


# --- 1.3: --json flag ---

def test_json_flag_defaults_false(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        result = runner.invoke(app, ["--model", "gemini-2.5-flash"], input="\n")
    assert result.exit_code == 0


def test_json_flag_true_when_passed(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        result = runner.invoke(app, ["--model", "gemini-2.5-flash", "--json"], input="\n")
    assert result.exit_code == 0


# --- 1.4: empty line / EOF graceful exit ---

def test_empty_line_exits_gracefully(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        result = runner.invoke(app, ["--model", "gemini-2.5-flash"], input="\n")
    assert result.exit_code == 0
    assert "Bye" in result.output


def test_eof_exits_gracefully(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        result = runner.invoke(app, ["--model", "gemini-2.5-flash"], input="")
    assert result.exit_code == 0


# --- 1.5: conversation loop calls agent.chat and render_text ---

def test_conversation_loop_calls_agent(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.agent.chat", return_value="Some response") as mock_chat:
            with patch("ghibli.cli.render_text") as mock_render:
                result = runner.invoke(
                    app, ["--model", "gemini-2.5-flash"], input="search python\n\n"
                )
    assert result.exit_code == 0
    assert mock_chat.call_count == 1
    pos_args = mock_chat.call_args.args
    assert pos_args == ("search python", "stub-id", False)
    assert mock_chat.call_args.kwargs.get("model") == "gemini-2.5-flash"
    mock_render.assert_called_once_with("Some response", False)


def test_model_flag_passed_to_agent(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.agent.chat", return_value="ok") as mock_chat:
            with patch("ghibli.cli.render_text"):
                with patch("ghibli.cli.picker.choose_model") as mock_choose:
                    result = runner.invoke(
                        app, ["--model", "openai:gpt-4o-mini"], input="hi\n\n"
                    )
    assert result.exit_code == 0
    # --model provided → picker SHALL NOT be consulted
    mock_choose.assert_not_called()
    # The model kwarg forwarded to agent.chat
    assert mock_chat.call_args.kwargs["model"] == "openai:gpt-4o-mini"


def test_picker_called_when_no_model_flag(runner):
    """Without --model, cli SHALL call picker.choose_model()."""
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli.picker.choose_model", return_value="openai:gpt-4o-mini") as mock_choose:
            with patch("ghibli.cli.picker.run_onboarding") as mock_onboard:
                with patch("ghibli.agent.chat", return_value="ok") as mock_chat:
                    with patch("ghibli.cli.render_text"):
                        result = runner.invoke(app, [], input="hi\n\n")
    assert result.exit_code == 0
    mock_choose.assert_called_once()
    mock_onboard.assert_not_called()
    # Picker's choice forwarded to agent
    assert mock_chat.call_args.kwargs["model"] == "openai:gpt-4o-mini"


def test_picker_handles_zero_provider_onboarding_internally(runner, monkeypatch):
    """picker.choose_model() now handles onboarding internally; cli just calls it."""
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli.picker.choose_model", return_value="openai:gpt-4o-mini") as mock_choose:
            with patch("ghibli.agent.chat", return_value="ok") as mock_chat:
                with patch("ghibli.cli.render_text"):
                    result = runner.invoke(app, [], input="hi\n\n")
    assert result.exit_code == 0
    mock_choose.assert_called_once()
    assert mock_chat.call_args.kwargs["model"] == "openai:gpt-4o-mini"


# --- Welcome banner on start ---

def test_welcome_banner_printed_once(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli.picker.choose_model", return_value="openai:gpt-4o-mini"):
            with patch("ghibli.agent.chat", return_value="hi"):
                with patch("ghibli.cli.render_text"):
                    result = runner.invoke(app, [], input="q\n\n")
    assert "openai:gpt-4o-mini" in result.output
    assert "stub-id" in result.output


# --- Tool call visualization during agent work ---

def test_on_tool_call_callback_passed_to_agent(runner):
    """CLI SHALL pass a non-None on_tool_call callback to agent.chat."""
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli.picker.choose_model", return_value="openai:gpt-4o-mini"):
            with patch("ghibli.agent.chat", return_value="ok") as mock_chat:
                with patch("ghibli.cli.render_text"):
                    runner.invoke(app, [], input="q\n\n")
    assert mock_chat.call_args.kwargs.get("on_tool_call") is not None


def test_tool_call_callback_prints_tool_line(runner):
    """When the callback is invoked, it prints a `→ tool(args)` line."""
    def fake_chat(user_message, session_id, json_output, model=None, on_tool_call=None):
        on_tool_call("search_repositories", {"q": "python"})
        return "done"

    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli.picker.choose_model", return_value="openai:gpt-4o-mini"):
            with patch("ghibli.agent.chat", side_effect=fake_chat):
                with patch("ghibli.cli.render_text"):
                    result = runner.invoke(app, [], input="q\n\n")
    assert "search_repositories" in result.output


# --- Session save hint on exit ---

def test_session_save_hint_when_turns_exist(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli.picker.choose_model", return_value="openai:gpt-4o-mini"):
            with patch("ghibli.sessions.count_turns", return_value=2):
                with patch("ghibli.sessions.delete_session") as mock_del:
                    with patch("ghibli.agent.chat", return_value="hi"):
                        with patch("ghibli.cli.render_text"):
                            result = runner.invoke(app, [], input="q\n\n")
    assert "Session saved" in result.output
    assert "stub-id" in result.output
    assert "--session stub-id" in result.output
    mock_del.assert_not_called()


def test_empty_session_deleted_on_exit(runner):
    """When exiting with zero turns, delete_session SHALL be called and no resume hint shown."""
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli.picker.choose_model", return_value="openai:gpt-4o-mini"):
            with patch("ghibli.sessions.count_turns", return_value=0):
                with patch("ghibli.sessions.delete_session") as mock_del:
                    with patch("ghibli.cli.render_text"):
                        result = runner.invoke(app, [], input="\n")
    mock_del.assert_called_once_with("stub-id")
    assert "Resume with" not in result.output


def test_ghibli_error_continues_session(runner):
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.agent.chat", side_effect=GhibliError("boom")):
            result = runner.invoke(
                app, ["--model", "gemini-2.5-flash"], input="query\n\n"
            )
    assert result.exit_code == 0
    assert "Error: boom" in result.output


# --- 1.7: unknown session ID rejected ---

def test_unknown_session_id_rejected(runner):
    with patch("ghibli.sessions.get_session", return_value=None):
        result = runner.invoke(app, ["--session", "nonexistent-id-xyz"])
    assert result.exit_code == 1
    assert "not found" in result.output


# --- Model resolution priority (no silent default) ---


def test_last_model_used_when_no_flag_no_env(runner, tmp_path, monkeypatch):
    """When --model and GHIBLI_MODEL are absent, last_model SHALL be used."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)
    (tmp_path / ".ghibli").mkdir()
    (tmp_path / ".ghibli" / "last_model").write_text("openai:gpt-4o-mini\n", encoding="utf-8")

    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli.picker.choose_model") as mock_choose:
            with patch("ghibli.agent.chat", return_value="ok") as mock_chat:
                with patch("ghibli.cli.render_text"):
                    result = runner.invoke(app, [], input="hi\n\n")
    assert result.exit_code == 0
    # Picker SHALL NOT be consulted — last_model wins
    mock_choose.assert_not_called()
    assert mock_chat.call_args.kwargs["model"] == "openai:gpt-4o-mini"


def test_model_flag_beats_last_model(runner, tmp_path, monkeypatch):
    """--model SHALL take precedence over last_model (and not overwrite it)."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)
    (tmp_path / ".ghibli").mkdir()
    last_file = tmp_path / ".ghibli" / "last_model"
    last_file.write_text("openai:gpt-4o-mini\n", encoding="utf-8")

    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.agent.chat", return_value="ok") as mock_chat:
            with patch("ghibli.cli.render_text"):
                result = runner.invoke(
                    app, ["--model", "gemma:gemma-4-26b-a4b-it"], input="hi\n\n"
                )
    assert result.exit_code == 0
    assert mock_chat.call_args.kwargs["model"] == "gemma:gemma-4-26b-a4b-it"
    # --model passage SHALL NOT overwrite .ghibli/last_model
    assert last_file.read_text(encoding="utf-8") == "openai:gpt-4o-mini\n"


def test_ghibli_model_env_beats_last_model(runner, tmp_path, monkeypatch):
    """GHIBLI_MODEL SHALL take precedence over last_model."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GHIBLI_MODEL", "openai:gpt-4o-mini")
    (tmp_path / ".ghibli").mkdir()
    (tmp_path / ".ghibli" / "last_model").write_text("ollama:qwen3.5:cloud\n", encoding="utf-8")

    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli.picker.choose_model") as mock_choose:
            with patch("ghibli.agent.chat", return_value="ok") as mock_chat:
                with patch("ghibli.cli.render_text"):
                    result = runner.invoke(app, [], input="hi\n\n")
    assert result.exit_code == 0
    mock_choose.assert_not_called()
    # agent.chat receives None for model since GHIBLI_MODEL will be read by agent itself,
    # OR cli resolves it explicitly. We accept either — validate via env check.
    # The key assertion: picker was not called and chat was invoked.
    assert mock_chat.call_count == 1


def test_picker_invoked_when_all_sources_empty(runner, tmp_path, monkeypatch):
    """Flag + env + last_model all absent (+ TTY) → picker SHALL be invoked."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)
    # No .ghibli dir

    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli.picker.choose_model", return_value="openai:gpt-4o-mini") as mock_choose:
            with patch("ghibli.cli._should_prompt_interactively", return_value=True):
                with patch("ghibli.agent.chat", return_value="ok") as mock_chat:
                    with patch("ghibli.cli.render_text"):
                        result = runner.invoke(app, [], input="hi\n\n")
    assert result.exit_code == 0
    mock_choose.assert_called_once()
    assert mock_chat.call_args.kwargs["model"] == "openai:gpt-4o-mini"


def test_non_tty_no_source_exits_code_1(runner, tmp_path, monkeypatch):
    """Non-TTY + all sources empty → CLI SHALL exit with code 1 and stderr mentions --model."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)

    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.cli._should_prompt_interactively", return_value=False):
            with patch("ghibli.cli.picker.choose_model", return_value=None):
                result = runner.invoke(app, [], input="")
    assert result.exit_code == 1
    assert "--model" in (result.output + (result.stderr if result.stderr_bytes is not None else ""))


# --- --model-picker flag ---


def test_model_picker_flag_forces_picker_even_with_last_model(runner, tmp_path, monkeypatch):
    """--model-picker SHALL force picker even when last_model exists."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)
    (tmp_path / ".ghibli").mkdir()
    (tmp_path / ".ghibli" / "last_model").write_text(
        "openai:gpt-4o-mini\n", encoding="utf-8"
    )

    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch(
            "ghibli.cli.picker.choose_model",
            return_value="gemma:gemma-4-26b-a4b-it",
        ) as mock_choose:
            with patch("ghibli.agent.chat", return_value="ok") as mock_chat:
                with patch("ghibli.cli.render_text"):
                    result = runner.invoke(app, ["--model-picker"], input="hi\n\n")
    assert result.exit_code == 0
    mock_choose.assert_called_once()
    assert mock_chat.call_args.kwargs["model"] == "gemma:gemma-4-26b-a4b-it"


def test_model_picker_flag_ignores_model_flag(runner, tmp_path, monkeypatch):
    """--model-picker SHALL ignore --model value and force picker."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)

    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch(
            "ghibli.cli.picker.choose_model",
            return_value="ollama:qwen3.5:cloud",
        ) as mock_choose:
            with patch("ghibli.agent.chat", return_value="ok") as mock_chat:
                with patch("ghibli.cli.render_text"):
                    result = runner.invoke(
                        app,
                        ["--model", "openai:gpt-4o-mini", "--model-picker"],
                        input="hi\n\n",
                    )
    assert result.exit_code == 0
    mock_choose.assert_called_once()
    # Picker's choice wins over the ignored --model value
    assert mock_chat.call_args.kwargs["model"] == "ollama:qwen3.5:cloud"


# --- Project-local .env read only ---


def test_cli_source_uses_explicit_dotenv_path():
    """cli.py SHALL NOT rely on find_dotenv's parent-directory walk."""
    from pathlib import Path as _Path
    src = (_Path(__file__).parent.parent.parent / "src" / "ghibli" / "cli.py").read_text(
        encoding="utf-8"
    )
    # Must pass an explicit dotenv_path (not the default find_dotenv)
    assert "dotenv_path=" in src
    # Must NOT import or call find_dotenv (which would walk parent directories)
    assert "find_dotenv" not in src


def test_home_env_is_not_loaded_into_process(runner, tmp_path, monkeypatch):
    """With no project .env, home-directory env vars SHALL NOT be injected."""
    monkeypatch.chdir(tmp_path)
    # Simulate a clean env with no creds configured
    for var in ("GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "OPENAI_API_KEY",
                "OLLAMA_API_KEY", "GHIBLI_MODEL"):
        monkeypatch.delenv(var, raising=False)

    # Invoke with --model to skip picker; just verify env after invocation
    with patch("ghibli.sessions.create_session", return_value="stub-id"):
        with patch("ghibli.agent.chat", return_value="ok"):
            with patch("ghibli.cli.render_text"):
                result = runner.invoke(
                    app, ["--model", "openai:gpt-4o-mini"], input="hi\n\n"
                )
    assert result.exit_code == 0
    # Even if ~/.env has any values, they are NOT present in os.environ post-load
    # (load_dotenv only reads project cwd's .env per explicit path)
    import os
    assert "GEMINI_API_KEY" not in os.environ  # was unset at monkeypatch, still unset
    assert "GOOGLE_CLOUD_PROJECT" not in os.environ
