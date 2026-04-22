"""TDD-RED tests for evals.models.chat_with_model.

evals/models.py does NOT exist yet — all tests are expected to fail
with ImportError (or a derivative).
"""
import os
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Guard import: if evals.models doesn't exist yet, every test fails with an
# explicit pytest.fail so pytest collects all tests AND reports them as FAILED
# (TDD-RED).  Once evals/models.py is created the import succeeds and the
# tests run for real.
# ---------------------------------------------------------------------------

try:
    from evals.models import chat_with_model
    _IMPORT_ERROR: Exception | None = None
except ImportError as exc:
    chat_with_model = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc

try:
    from ghibli.exceptions import ToolCallError
except ImportError:
    ToolCallError = Exception  # type: ignore[assignment,misc]


def _require_module() -> None:
    """Call at the top of every test — raises pytest.fail if evals.models missing."""
    if _IMPORT_ERROR is not None:
        pytest.fail(f"evals.models not yet implemented: {_IMPORT_ERROR}")


# ---------------------------------------------------------------------------
# Helper: build a minimal fake litellm response with no tool calls
# ---------------------------------------------------------------------------

def _make_fake_litellm_response(text: str = "ok") -> MagicMock:
    """Return a MagicMock that looks like a litellm ModelResponse."""
    choice = MagicMock()
    choice.message.content = text
    choice.message.tool_calls = None  # no tool calls → loop exits immediately

    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestChatWithModelRouting:
    """chat_with_model() passes the correct model ID to litellm.completion."""

    @patch("evals.models.litellm.completion")
    def test_gemini_uses_correct_model_id(self, mock_completion: MagicMock) -> None:
        _require_module()
        mock_completion.return_value = _make_fake_litellm_response()

        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
            chat_with_model("hello", session_id="s1", model_name="gemini")

        called_model = mock_completion.call_args[1].get(
            "model", mock_completion.call_args[0][0] if mock_completion.call_args[0] else None
        )
        assert called_model == "gemini/gemini-2.5-flash"

    @patch("evals.models.litellm.completion")
    def test_gemma4_uses_correct_model_id(self, mock_completion: MagicMock) -> None:
        _require_module()
        mock_completion.return_value = _make_fake_litellm_response()

        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
            chat_with_model("hello", session_id="s1", model_name="gemma4")

        called_model = mock_completion.call_args[1].get(
            "model", mock_completion.call_args[0][0] if mock_completion.call_args[0] else None
        )
        assert called_model == "gemini/gemma-4-26b-a4b-it"

    @patch("evals.models.litellm.completion")
    def test_gpt4o_mini_uses_correct_model_id(self, mock_completion: MagicMock) -> None:
        _require_module()
        mock_completion.return_value = _make_fake_litellm_response()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
            chat_with_model("hello", session_id="s1", model_name="gpt4o-mini")

        called_model = mock_completion.call_args[1].get(
            "model", mock_completion.call_args[0][0] if mock_completion.call_args[0] else None
        )
        assert called_model == "openai/gpt-4o-mini"

    @patch("evals.models.litellm.completion")
    def test_ollama_cloud_uses_correct_model_id(self, mock_completion: MagicMock) -> None:
        _require_module()
        mock_completion.return_value = _make_fake_litellm_response()

        with patch.dict(os.environ, {"OLLAMA_API_KEY": "test-key", "OLLAMA_CLOUD_MODEL": "llama3.1:8b"}):
            chat_with_model("hello", session_id="s1", model_name="ollama-cloud")

        kwargs = mock_completion.call_args[1]
        assert kwargs.get("model") == "ollama_chat/llama3.1:8b"
        assert kwargs.get("api_base") == "https://ollama.com"
        assert kwargs.get("api_key") == "test-key"


class TestChatWithModelUnknownModel:
    """Unknown model_name raises ToolCallError mentioning valid model names."""

    def test_unknown_model_raises_tool_call_error(self) -> None:
        _require_module()
        with pytest.raises(ToolCallError) as exc_info:
            chat_with_model("hello", session_id="s1", model_name="unknown")

        error_msg = str(exc_info.value).lower()
        # The error message should hint at valid options
        assert any(
            name in error_msg
            for name in ("gemini", "gemma4", "gpt4o-mini", "valid")
        ), f"Error message did not mention valid model names: {exc_info.value}"


class TestChatWithModelMissingApiKey:
    """Missing environment API keys raise ToolCallError with the key name."""

    @patch("evals.models.litellm.completion")
    def test_missing_gemini_api_key_raises(self, _mock: MagicMock) -> None:
        _require_module()
        env_without_key = {
            k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"
        }
        with patch.dict(os.environ, env_without_key, clear=True):
            with pytest.raises(ToolCallError) as exc_info:
                chat_with_model("hello", session_id="s1", model_name="gemini")

        assert "GEMINI_API_KEY" in str(exc_info.value)

    @patch("evals.models.litellm.completion")
    def test_missing_gemini_key_raises_for_gemma4(self, _mock: MagicMock) -> None:
        _require_module()
        env_without_key = {
            k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"
        }
        with patch.dict(os.environ, env_without_key, clear=True):
            with pytest.raises(ToolCallError) as exc_info:
                chat_with_model("hello", session_id="s1", model_name="gemma4")

        assert "GEMINI_API_KEY" in str(exc_info.value)


class TestChatWithModelReturnType:
    """chat_with_model() returns (str, list[str]) — text reply + list of tool call names used."""

    @patch("evals.models.litellm.completion")
    def test_return_type_is_tuple_of_str_and_list(self, mock_completion: MagicMock) -> None:
        _require_module()
        mock_completion.return_value = _make_fake_litellm_response("hello back")

        with patch.dict(os.environ, {"GEMINI_API_KEY": "fake-key"}):
            result = chat_with_model("hello", session_id="s1", model_name="gemini")

        assert isinstance(result, tuple), "Expected a tuple return value"
        assert len(result) == 2, "Expected a 2-tuple (reply, tool_calls)"
        reply, tool_calls = result
        assert isinstance(reply, str)
        assert isinstance(tool_calls, list)
