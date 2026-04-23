"""Tests for ghibli.picker — model picker, onboarding flow, and .env writer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ghibli.exceptions import SessionError
from ghibli.picker import (
    append_env_var,
    choose_model,
    read_last_model,
    run_onboarding,
    write_last_model,
)


# --- append_env_var ---


def test_append_env_var_creates_file_when_absent(tmp_path: Path):
    env = tmp_path / ".env"
    append_env_var("GEMINI_API_KEY", "AI123", env_path=env)
    assert env.read_text(encoding="utf-8") == "GEMINI_API_KEY=AI123\n"


def test_append_env_var_appends_when_key_missing(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=sk-existing\n", encoding="utf-8")
    append_env_var("GEMINI_API_KEY", "AI123", env_path=env)
    assert env.read_text(encoding="utf-8") == (
        "OPENAI_API_KEY=sk-existing\nGEMINI_API_KEY=AI123\n"
    )


def test_append_env_var_adds_leading_newline_if_file_lacks_trailing_newline(tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=sk-old", encoding="utf-8")  # no trailing \n
    append_env_var("GEMINI_API_KEY", "AI123", env_path=env)
    content = env.read_text(encoding="utf-8")
    assert content.endswith("GEMINI_API_KEY=AI123\n")
    assert "OPENAI_API_KEY=sk-old\nGEMINI_API_KEY=AI123\n" == content


def test_append_env_var_refuses_to_overwrite_existing_key(tmp_path: Path):
    env = tmp_path / ".env"
    original = "GEMINI_API_KEY=AI-old\n"
    env.write_text(original, encoding="utf-8")

    with pytest.raises(SessionError) as exc:
        append_env_var("GEMINI_API_KEY", "AI-new", env_path=env)

    # File must be unchanged
    assert env.read_text(encoding="utf-8") == original
    assert "GEMINI_API_KEY" in str(exc.value)


# --- choose_model ---


def test_choose_model_returns_none_when_stdin_not_tty(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    with patch("ghibli.picker.sys.stdin.isatty", return_value=False):
        assert choose_model() is None


def test_choose_model_returns_none_when_ghibli_model_set(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GHIBLI_MODEL", "openai:gpt-4o-mini")
    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        assert choose_model() is None


def _make_prompt_stub(choice: int, key: str = "fake-key", slug: str | None = None):
    """Returns a typer.prompt substitute.

    - hide_input=True → return `key` (API key paste)
    - type=int → return `choice` (numbered menu)
    - else → return `slug` if explicitly given, otherwise the prompt's `default`
      (so callers who want to "accept the default" pass slug=None)
    """
    def stub(text, default=None, type=None, hide_input=False, **kwargs):
        if hide_input:
            return key
        if type is int:
            return choice
        if slug is not None:
            return slug
        return default if default is not None else ""
    return stub


def test_choose_model_always_shows_5_options_regardless_of_env(monkeypatch, capsys, tmp_path):
    """Redesigned picker lists all 5 providers every time (no env filtering)."""
    monkeypatch.chdir(tmp_path)
    # Set all creds so onboarding doesn't run and pollute the test
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "p")
    monkeypatch.setenv("OPENAI_API_KEY", "y")
    monkeypatch.setenv("OLLAMA_API_KEY", "z")
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)

    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt", side_effect=_make_prompt_stub(1)):
            choose_model()

    out = capsys.readouterr().out
    assert "1)" in out and "Gemini 2.5 Flash (API Key)" in out
    assert "2)" in out and "Vertex AI" in out
    assert "3)" in out and "Gemma" in out
    assert "4)" in out and "OpenAI" in out
    assert "5)" in out and "Ollama" in out


def test_choose_model_option_mapping(monkeypatch, tmp_path):
    """Each numbered choice maps to the expected model identifier."""
    monkeypatch.chdir(tmp_path)
    # Pre-set all creds so onboarding doesn't fire during this mapping test
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "p")
    monkeypatch.setenv("OPENAI_API_KEY", "y")
    monkeypatch.setenv("OLLAMA_API_KEY", "z")
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_CLOUD_MODEL", raising=False)

    expected = {
        1: "gemini-2.5-flash",
        2: "gemini-2.5-flash",  # Vertex AI uses same identifier; routing differs via env
        3: "gemini:gemma-4-26b-a4b-it",
        4: "openai:gpt-4o-mini",
        5: "ollama:qwen3.5:cloud",
    }
    for choice, identifier in expected.items():
        with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
            with patch("ghibli.picker.typer.prompt", side_effect=_make_prompt_stub(choice)):
                result = choose_model()
        assert result == identifier, f"option {choice} → {result!r}, expected {identifier!r}"


def test_choose_model_writes_last_model(monkeypatch, tmp_path):
    """After user picks, <cwd>/.ghibli/last_model is written with the identifier."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "y")
    for var in ("GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "OLLAMA_API_KEY", "GHIBLI_MODEL"):
        monkeypatch.delenv(var, raising=False)

    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt", side_effect=_make_prompt_stub(4)):
            choose_model()

    last_file = tmp_path / ".ghibli" / "last_model"
    assert last_file.exists()
    assert last_file.read_text(encoding="utf-8") == "openai:gpt-4o-mini\n"


# --- run_onboarding ---


def test_run_onboarding_writes_key_and_returns_model(monkeypatch, tmp_path: Path, capsys):
    env = tmp_path / ".env"
    monkeypatch.chdir(tmp_path)
    # All creds absent so picker selection triggers onboarding
    for var in ("GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "OPENAI_API_KEY",
                "OLLAMA_API_KEY", "GHIBLI_MODEL"):
        monkeypatch.delenv(var, raising=False)

    def fake_prompt(text, default=None, type=None, hide_input=False, **kwargs):
        if hide_input:
            return "sk-new"
        if type is int:
            return 4  # OpenAI in the new 5-option ordering
        # Slug prompt — accept the prompt's default ("gpt-4o-mini")
        return default

    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt", side_effect=fake_prompt):
            result = run_onboarding()

    assert result == "openai:gpt-4o-mini"
    assert env.read_text(encoding="utf-8") == "OPENAI_API_KEY=sk-new\n"


def test_run_onboarding_aborts_when_key_already_exists(monkeypatch, tmp_path: Path):
    env = tmp_path / ".env"
    env.write_text("OPENAI_API_KEY=sk-existing\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)  # force onboarding path
    for var in ("GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "OLLAMA_API_KEY",
                "GHIBLI_MODEL"):
        monkeypatch.delenv(var, raising=False)

    def fake_prompt(text, default=None, type=None, hide_input=False):
        if hide_input:
            return "sk-new"
        return 4  # OpenAI

    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt", side_effect=fake_prompt):
            with pytest.raises(SystemExit) as exc:
                run_onboarding()

    assert exc.value.code == 0
    # File must not be modified
    assert env.read_text(encoding="utf-8") == "OPENAI_API_KEY=sk-existing\n"


# --- read_last_model / write_last_model ---


def test_read_last_model_returns_none_when_absent(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    # No .ghibli directory at all
    assert read_last_model() is None


def test_read_last_model_strips_trailing_whitespace(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ghibli_dir = tmp_path / ".ghibli"
    ghibli_dir.mkdir()
    (ghibli_dir / "last_model").write_text("openai:gpt-4o-mini\n", encoding="utf-8")
    assert read_last_model() == "openai:gpt-4o-mini"


def test_read_last_model_returns_none_when_empty(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    ghibli_dir = tmp_path / ".ghibli"
    ghibli_dir.mkdir()
    (ghibli_dir / "last_model").write_text("", encoding="utf-8")
    assert read_last_model() is None


def test_write_last_model_creates_dir_and_file(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert not (tmp_path / ".ghibli").exists()
    write_last_model("openai:gpt-4o-mini")
    assert (tmp_path / ".ghibli" / "last_model").read_text(encoding="utf-8") == "openai:gpt-4o-mini\n"


def test_write_then_read_round_trip(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_last_model("gemini:gemma-4-26b-a4b-it")
    assert read_last_model() == "gemini:gemma-4-26b-a4b-it"


def test_write_last_model_overwrites_previous(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_last_model("openai:gpt-4o-mini")
    write_last_model("ollama:qwen3.5:cloud")
    assert read_last_model() == "ollama:qwen3.5:cloud"


# --- Vertex AI onboarding ---


def test_vertex_onboarding_prints_gcloud_instruction(monkeypatch, tmp_path, capsys):
    """Selecting option 2 (Vertex AI) without GOOGLE_CLOUD_PROJECT triggers ADC guidance."""
    monkeypatch.chdir(tmp_path)
    for var in ("GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION",
                "OPENAI_API_KEY", "OLLAMA_API_KEY", "GHIBLI_MODEL"):
        monkeypatch.delenv(var, raising=False)

    def fake_prompt(text, default=None, type=None, hide_input=False, **kwargs):
        if type is int:
            return 2  # Vertex AI
        # Text prompts in order: "Press Enter when done" → project id → location
        if "Project" in text or "PROJECT" in text:
            return "my-project"
        if "LOCATION" in text or "location" in text:
            return default or "us-central1"  # accept default
        return ""  # Press Enter confirmation

    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt", side_effect=fake_prompt):
            result = choose_model()

    out = capsys.readouterr().out
    assert "gcloud auth application-default login" in out
    assert result == "gemini-2.5-flash"

    # .env should contain only GOOGLE_CLOUD_PROJECT (location accepted default → not written)
    env_content = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "GOOGLE_CLOUD_PROJECT=my-project" in env_content
    assert "GOOGLE_CLOUD_LOCATION" not in env_content


def test_vertex_onboarding_writes_custom_location(monkeypatch, tmp_path):
    """Non-default location value SHALL be persisted."""
    monkeypatch.chdir(tmp_path)
    for var in ("GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "GOOGLE_CLOUD_LOCATION",
                "OPENAI_API_KEY", "OLLAMA_API_KEY", "GHIBLI_MODEL"):
        monkeypatch.delenv(var, raising=False)

    def fake_prompt(text, default=None, type=None, hide_input=False, **kwargs):
        if type is int:
            return 2
        if "PROJECT" in text:
            return "p"
        if "LOCATION" in text:
            return "europe-west4"  # custom
        return ""

    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt", side_effect=fake_prompt):
            choose_model()

    env_content = (tmp_path / ".env").read_text(encoding="utf-8")
    assert "GOOGLE_CLOUD_PROJECT=p" in env_content
    assert "GOOGLE_CLOUD_LOCATION=europe-west4" in env_content


# --- ensure_credentials ---


def test_ensure_credentials_noop_when_openai_key_present(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    from ghibli.picker import ensure_credentials
    # No exception, no onboarding
    ensure_credentials("openai:gpt-4o-mini")


def test_ensure_credentials_onboards_openai_when_missing_on_tty(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def fake_prompt(text, default=None, type=None, hide_input=False, **kwargs):
        if hide_input:
            return "sk-new"
        return ""

    from ghibli.picker import ensure_credentials
    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt", side_effect=fake_prompt):
            ensure_credentials("openai:gpt-4o-mini")

    assert (tmp_path / ".env").read_text(encoding="utf-8") == "OPENAI_API_KEY=sk-new\n"


def test_ensure_credentials_raises_on_non_tty_when_missing(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from ghibli.picker import ensure_credentials
    with patch("ghibli.picker.sys.stdin.isatty", return_value=False):
        with pytest.raises(SessionError) as exc:
            ensure_credentials("openai:gpt-4o-mini")
    assert "OPENAI_API_KEY" in str(exc.value)


def test_ensure_credentials_bare_gemini_accepts_either_env(monkeypatch):
    """Bare gemini-2.5-flash is satisfied by GEMINI_API_KEY OR GOOGLE_CLOUD_PROJECT."""
    from ghibli.picker import ensure_credentials

    # Only GEMINI_API_KEY → OK
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    ensure_credentials("gemini-2.5-flash")

    # Only GOOGLE_CLOUD_PROJECT → OK
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "p")
    ensure_credentials("gemini-2.5-flash")


def test_ensure_credentials_bare_gemini_raises_when_neither_env_set(monkeypatch):
    from ghibli.picker import ensure_credentials
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with patch("ghibli.picker.sys.stdin.isatty", return_value=False):
        with pytest.raises(SessionError) as exc:
            ensure_credentials("gemini-2.5-flash")
    assert "GEMINI_API_KEY" in str(exc.value)


# --- OPENAI_MODEL env var customization ---


def test_choose_model_openai_default_is_gpt_4o_mini(monkeypatch, tmp_path):
    """Without OPENAI_MODEL set, option 4 resolves to openai:gpt-4o-mini."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    for var in ("GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "OLLAMA_API_KEY",
                "GHIBLI_MODEL", "OPENAI_MODEL"):
        monkeypatch.delenv(var, raising=False)

    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt", side_effect=_make_prompt_stub(4)):
            result = choose_model()
    assert result == "openai:gpt-4o-mini"


def test_choose_model_openai_respects_OPENAI_MODEL_env(monkeypatch, tmp_path):
    """OPENAI_MODEL=gpt-4o → option 4 resolves to openai:gpt-4o."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
    for var in ("GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "OLLAMA_API_KEY", "GHIBLI_MODEL"):
        monkeypatch.delenv(var, raising=False)

    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt", side_effect=_make_prompt_stub(4)):
            result = choose_model()
    assert result == "openai:gpt-4o"


def test_picker_prompts_for_openai_slug_with_env_default(monkeypatch, tmp_path):
    """Selecting OpenAI SHALL prompt for model slug; default comes from OPENAI_MODEL env."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")
    for var in ("GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "OLLAMA_API_KEY", "GHIBLI_MODEL"):
        monkeypatch.delenv(var, raising=False)

    # choice=4 picks OpenAI; slug prompt is answered with the prompt's default (env value)
    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt", side_effect=_make_prompt_stub(4)):
            result = choose_model()
    assert result == "openai:gpt-4-turbo"


def test_picker_prompts_for_openai_slug_user_can_override(monkeypatch, tmp_path):
    """User can type a different slug instead of accepting the env default."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-x")
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    for var in ("GEMINI_API_KEY", "GOOGLE_CLOUD_PROJECT", "OLLAMA_API_KEY", "GHIBLI_MODEL"):
        monkeypatch.delenv(var, raising=False)

    with patch("ghibli.picker.sys.stdin.isatty", return_value=True):
        with patch("ghibli.picker.typer.prompt",
                   side_effect=_make_prompt_stub(4, slug="gpt-5")):
            result = choose_model()
    assert result == "openai:gpt-5"
