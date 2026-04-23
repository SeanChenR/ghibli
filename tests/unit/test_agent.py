import os
from unittest.mock import MagicMock, patch

import pytest

from ghibli.agent import chat
from ghibli.exceptions import ToolCallError


@pytest.fixture(autouse=True)
def mock_sessions():
    with patch("ghibli.agent.sessions.get_turns", return_value=[]):
        with patch("ghibli.agent.sessions.append_turn"):
            yield


# --- 1.4: missing credentials raises ToolCallError ---

def test_missing_credentials_raises_tool_call_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
    with pytest.raises(ToolCallError) as exc_info:
        chat("hello", "s1", False, model="gemini-2.5-flash")
    msg = str(exc_info.value)
    assert "GEMINI_API_KEY" in msg
    assert "GOOGLE_CLOUD_PROJECT" in msg


# --- 1.5: API key mode initializes client ---

def test_api_key_mode_initializes_client(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    mock_response = MagicMock()
    mock_response.function_calls = []
    mock_response.text = "Hello!"

    with patch("ghibli.agent.genai.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

        result = chat("hello", "s1", False, model="gemini-2.5-flash")

    MockClient.assert_called_once_with(api_key="test_key")
    assert result == "Hello!"


# --- 1.6: Vertex AI mode initializes client ---

def test_vertex_mode_initializes_client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)

    mock_response = MagicMock()
    mock_response.function_calls = []
    mock_response.text = "Hello!"

    with patch("ghibli.agent.genai.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

        result = chat("hello", "s1", False, model="gemini-2.5-flash")

    MockClient.assert_called_once_with(
        vertexai=True, project="my-project", location="us-central1"
    )


# --- 1.7: no tool call returns text ---

def test_no_tool_call_returns_text(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    mock_response = MagicMock()
    mock_response.function_calls = []
    mock_response.text = "I can help you search GitHub!"

    with patch("ghibli.agent.genai.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

        result = chat("hello", "s1", False, model="gemini-2.5-flash")

    assert result == "I can help you search GitHub!"


# --- 1.8: function calling loop executes tool ---

def test_function_calling_loop_executes_tool(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    mock_fc = MagicMock()
    mock_fc.name = "search_repositories"
    mock_fc.args = {"q": "python"}

    mock_response1 = MagicMock()
    mock_response1.function_calls = [mock_fc]

    mock_response2 = MagicMock()
    mock_response2.function_calls = []
    mock_response2.text = "Found Python repos!"

    with patch("ghibli.agent.genai.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.models.generate_content.side_effect = [mock_response1, mock_response2]

        with patch("ghibli.agent.tools.search_repositories", return_value={"items": []}) as mock_tool:
            result = chat("search python", "s1", False, model="gemini-2.5-flash")

    mock_tool.assert_called_once_with(q="python")
    assert result == "Found Python repos!"


# --- 1.9: session history loaded and turns saved after response ---

def test_session_history_appended_after_response(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    mock_response = MagicMock()
    mock_response.function_calls = []
    mock_response.text = "Got it!"

    with patch("ghibli.agent.genai.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.models.generate_content.return_value = mock_response

        with patch("ghibli.agent.sessions.get_turns", return_value=[]) as mock_get:
            with patch("ghibli.agent.sessions.append_turn") as mock_append:
                chat("hi", "sess-1", False, model="gemini-2.5-flash")

    mock_get.assert_called_once_with("sess-1")
    assert mock_append.call_count == 2
    calls = [c.args for c in mock_append.call_args_list]
    assert calls[0] == ("sess-1", "user", "hi")
    assert calls[1] == ("sess-1", "assistant", "Got it!")


# --- Ollama Cloud routing ---

def _make_litellm_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.tool_calls = None
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def test_ollama_cloud_routing_uses_litellm(monkeypatch):
    """GHIBLI_MODEL=ollama:<model> must route through LiteLLM, not Gemini SDK."""
    monkeypatch.setenv("GHIBLI_MODEL", "ollama:llama3.1:8b")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-ollama-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with patch("ghibli.agent.litellm.completion", return_value=_make_litellm_response("Hi!")) as mock_litellm:
        with patch("ghibli.agent.genai.Client") as mock_gemini:
            result = chat("hello", "s1", False)

    mock_litellm.assert_called_once()
    mock_gemini.assert_not_called()
    assert result == "Hi!"


def test_ollama_cloud_model_id_constructed_correctly(monkeypatch):
    """Model ID passed to LiteLLM must be ollama_chat/<slug> and api_base set."""
    monkeypatch.setenv("GHIBLI_MODEL", "ollama:qwen2.5:7b")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")

    with patch("ghibli.agent.litellm.completion", return_value=_make_litellm_response("ok")) as mock_lit:
        chat("test", "s1", False)

    kwargs = mock_lit.call_args[1]
    assert kwargs["model"] == "ollama_chat/qwen2.5:7b"
    assert kwargs["api_base"] == "https://ollama.com"
    assert kwargs["api_key"] == "test-key"


def test_ollama_cloud_missing_api_key_raises(monkeypatch):
    """Missing OLLAMA_API_KEY must raise ToolCallError with helpful message."""
    monkeypatch.setenv("GHIBLI_MODEL", "ollama:llama3.1:8b")
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ToolCallError) as exc_info:
        chat("hello", "s1", False)

    assert "OLLAMA_API_KEY" in str(exc_info.value)


def test_ollama_cloud_session_saved(monkeypatch):
    """Ollama Cloud path must save user + assistant turns to the session."""
    monkeypatch.setenv("GHIBLI_MODEL", "ollama:llama3.1:8b")
    monkeypatch.setenv("OLLAMA_API_KEY", "test-key")

    with patch("ghibli.agent.litellm.completion", return_value=_make_litellm_response("Done!")):
        with patch("ghibli.agent.sessions.get_turns", return_value=[]) as mock_get:
            with patch("ghibli.agent.sessions.append_turn") as mock_append:
                result = chat("query", "sess-2", False)

    mock_get.assert_called_once_with("sess-2")
    assert mock_append.call_count == 2
    calls = [c.args for c in mock_append.call_args_list]
    assert calls[0] == ("sess-2", "user", "query")
    assert calls[1] == ("sess-2", "assistant", "Done!")
    assert result == "Done!"


# --- OpenAI routing ---


def test_openai_routing_uses_litellm(monkeypatch):
    """GHIBLI_MODEL=openai:<model> must route through LiteLLM, not Gemini SDK."""
    monkeypatch.setenv("GHIBLI_MODEL", "openai:gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with patch("ghibli.agent.litellm.completion", return_value=_make_litellm_response("Hi!")) as mock_litellm:
        with patch("ghibli.agent.genai.Client") as mock_gemini:
            result = chat("hello", "s1", False)

    mock_litellm.assert_called_once()
    mock_gemini.assert_not_called()
    assert result == "Hi!"


def test_openai_model_id_constructed_correctly(monkeypatch):
    """Model ID passed to LiteLLM must be openai/<slug>; no api_base for OpenAI."""
    monkeypatch.setenv("GHIBLI_MODEL", "openai:gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    with patch("ghibli.agent.litellm.completion", return_value=_make_litellm_response("ok")) as mock_lit:
        chat("test", "s1", False)

    kwargs = mock_lit.call_args[1]
    assert kwargs["model"] == "openai/gpt-4o-mini"
    assert kwargs["api_key"] == "sk-test"
    assert "api_base" not in kwargs


def test_openai_missing_api_key_raises(monkeypatch):
    """Missing OPENAI_API_KEY must raise ToolCallError with helpful message."""
    monkeypatch.setenv("GHIBLI_MODEL", "openai:gpt-4o-mini")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ToolCallError) as exc_info:
        chat("hello", "s1", False)

    assert "OPENAI_API_KEY" in str(exc_info.value)


# --- explicit model= param overrides env var ---


# --- tool errors are recoverable within a turn ---


def _github_api_side_effect(tool_name, args):
    """Simulate get_repository 404 + search_repositories success."""
    if tool_name == "get_repository":
        raise Exception("Client error '404 Not Found'")
    if tool_name == "search_repositories":
        return {"items": [{"full_name": "spectra-app/spectra-app"}]}
    return {}


def test_gemini_tool_error_recovers_within_turn(monkeypatch):
    """When a tool raises, error must be passed back to model (not raise ToolCallError)
    so the model can retry. Session turns must still be saved at end."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")

    failing_fc = MagicMock()
    failing_fc.name = "get_repository"
    failing_fc.args = {"owner": "Spectra-app", "repo": "spectra"}

    retry_fc = MagicMock()
    retry_fc.name = "search_repositories"
    retry_fc.args = {"q": "spectra-app"}

    r1 = MagicMock(function_calls=[failing_fc])
    r2 = MagicMock(function_calls=[retry_fc])
    r3 = MagicMock(function_calls=[], text="Found it!")

    with patch("ghibli.agent.genai.Client") as MockClient:
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        mock_client.models.generate_content.side_effect = [r1, r2, r3]

        with patch("ghibli.github_api.execute", side_effect=_github_api_side_effect):
            with patch("ghibli.agent.sessions.append_turn") as mock_append:
                result = chat("spectra-app repo", "s1", False, model="gemini-2.5-flash")

    assert result == "Found it!"
    assert mock_client.models.generate_content.call_count == 3
    assert mock_append.call_count == 2  # user + assistant both saved


def test_litellm_tool_error_recovers_within_turn(monkeypatch):
    """Same recovery behavior on OpenAI / Ollama path."""
    monkeypatch.setenv("GHIBLI_MODEL", "openai:gpt-4o-mini")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    fail_tc = MagicMock()
    fail_tc.id = "t1"
    fail_tc.function.name = "get_repository"
    fail_tc.function.arguments = '{"owner": "Spectra-app", "repo": "spectra"}'

    fail_msg = MagicMock()
    fail_msg.tool_calls = [fail_tc]
    fail_msg.content = None
    r1 = MagicMock(choices=[MagicMock(message=fail_msg)])

    r2 = _make_litellm_response("Recovered!")

    with patch("ghibli.agent.litellm.completion", side_effect=[r1, r2]):
        with patch("ghibli.github_api.execute", side_effect=_github_api_side_effect):
            with patch("ghibli.agent.sessions.append_turn") as mock_append:
                result = chat("spectra-app", "s1", False)

    assert result == "Recovered!"
    assert mock_append.call_count == 2


def test_explicit_model_overrides_env_var(monkeypatch):
    """model= kwarg must take precedence over GHIBLI_MODEL env var."""
    monkeypatch.setenv("GHIBLI_MODEL", "gemini-2.5-flash")     # would route to Gemini
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with patch("ghibli.agent.litellm.completion", return_value=_make_litellm_response("ok")) as mock_lit:
        with patch("ghibli.agent.genai.Client") as mock_gemini:
            chat("hello", "s1", False, model="openai:gpt-4o-mini")

    mock_gemini.assert_not_called()
    assert mock_lit.call_args[1]["model"] == "openai/gpt-4o-mini"


# --- gemini: prefix routes chat to LiteLLM with Gemini provider ---


def test_gemini_prefix_routes_through_litellm(monkeypatch):
    """gemini:<slug> must route through LiteLLM with model=gemini/<slug>."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)

    with patch("ghibli.agent.litellm.completion", return_value=_make_litellm_response("ok")) as mock_lit:
        with patch("ghibli.agent.genai.Client") as mock_gemini:
            result = chat("hi", "s1", False, model="gemini:gemma-4-26b-a4b-it")

    mock_gemini.assert_not_called()
    kwargs = mock_lit.call_args[1]
    assert kwargs["model"] == "gemini/gemma-4-26b-a4b-it"
    assert kwargs["api_key"] == "test-gemini-key"
    assert "api_base" not in kwargs
    assert result == "ok"


def test_bare_gemini_model_still_uses_native_sdk(monkeypatch):
    """Bare gemini-2.5-flash (no gemini: prefix) must use native google.genai.Client."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)

    mock_resp = MagicMock()
    mock_resp.function_calls = []
    mock_resp.text = "hello"

    with patch("ghibli.agent.genai.Client") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.models.generate_content.return_value = mock_resp

        with patch("ghibli.agent.litellm.completion") as mock_lit:
            result = chat("hi", "s1", False, model="gemini-2.5-flash")

    MockClient.assert_called_once_with(api_key="test-gemini-key")
    mock_lit.assert_not_called()
    assert result == "hello"


def test_gemini_prefix_missing_api_key_raises(monkeypatch):
    """gemini: prefix without GEMINI_API_KEY must raise ToolCallError."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GHIBLI_MODEL", raising=False)

    with pytest.raises(ToolCallError) as exc_info:
        chat("hi", "s1", False, model="gemini:gemma-4-26b-a4b-it")

    assert "GEMINI_API_KEY" in str(exc_info.value)


# --- on_tool_call callback invoked per tool dispatch ---


def test_on_tool_call_gemini_path_invoked_per_dispatch(monkeypatch):
    """Gemini native SDK path must invoke on_tool_call for every function call dispatched."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")

    fc1 = MagicMock()
    fc1.name = "search_repositories"
    fc1.args = {"q": "python"}

    fc2 = MagicMock()
    fc2.name = "get_repository"
    fc2.args = {"owner": "x", "repo": "y"}

    r1 = MagicMock(function_calls=[fc1, fc2])
    r2 = MagicMock(function_calls=[], text="Done!")

    calls: list = []

    def cb(name, args):
        calls.append((name, dict(args)))

    with patch("ghibli.agent.genai.Client") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.models.generate_content.side_effect = [r1, r2]

        with patch("ghibli.agent.tools.search_repositories", return_value={"items": []}):
            with patch("ghibli.agent.tools.get_repository", return_value={"full_name": "x/y"}):
                result = chat("q", "s1", False, model="gemini-2.5-flash", on_tool_call=cb)

    assert result == "Done!"
    assert calls == [
        ("search_repositories", {"q": "python"}),
        ("get_repository", {"owner": "x", "repo": "y"}),
    ]


def test_on_tool_call_litellm_path_invoked_per_dispatch(monkeypatch):
    """LiteLLM path (openai: / ollama: / gemini:) must also invoke on_tool_call."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

    tc = MagicMock()
    tc.id = "t1"
    tc.function.name = "search_repositories"
    tc.function.arguments = '{"q": "python"}'

    msg1 = MagicMock()
    msg1.tool_calls = [tc]
    msg1.content = None
    r1 = MagicMock(choices=[MagicMock(message=msg1)])

    r2 = _make_litellm_response("All good!")

    calls: list = []

    def cb(name, args):
        calls.append((name, dict(args)))

    with patch("ghibli.agent.litellm.completion", side_effect=[r1, r2]):
        with patch("ghibli.github_api.execute", return_value={"items": []}):
            result = chat("q", "s1", False, model="openai:gpt-4o-mini", on_tool_call=cb)

    assert result == "All good!"
    assert calls == [("search_repositories", {"q": "python"})]


def test_on_tool_call_default_none_keeps_legacy_behavior(monkeypatch):
    """Without on_tool_call, chat() behavior is unchanged (no attribute errors)."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")

    r = MagicMock(function_calls=[], text="Hi")

    with patch("ghibli.agent.genai.Client") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.models.generate_content.return_value = r

        # No on_tool_call kwarg — must work exactly as before
        result = chat("hi", "s1", False, model="gemini-2.5-flash")

    assert result == "Hi"


def test_on_tool_call_exception_does_not_break_loop(monkeypatch, capsys):
    """If the callback raises, chat() must still complete normally and log to stderr."""
    monkeypatch.setenv("GEMINI_API_KEY", "test_key")

    fc = MagicMock()
    fc.name = "search_repositories"
    fc.args = {"q": "python"}

    r1 = MagicMock(function_calls=[fc])
    r2 = MagicMock(function_calls=[], text="Survived!")

    def broken_cb(name, args):
        raise RuntimeError("boom")

    with patch("ghibli.agent.genai.Client") as MockClient:
        client = MagicMock()
        MockClient.return_value = client
        client.models.generate_content.side_effect = [r1, r2]

        with patch("ghibli.agent.tools.search_repositories", return_value={"items": []}):
            result = chat("q", "s1", False, model="gemini-2.5-flash", on_tool_call=broken_cb)

    assert result == "Survived!"
    # Callback error should have been written to stderr
    captured = capsys.readouterr()
    assert "boom" in captured.err
