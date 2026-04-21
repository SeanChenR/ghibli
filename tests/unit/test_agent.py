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
        chat("hello", "s1", False)
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

        result = chat("hello", "s1", False)

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

        result = chat("hello", "s1", False)

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

        result = chat("hello", "s1", False)

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
            result = chat("search python", "s1", False)

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
                chat("hi", "sess-1", False)

    mock_get.assert_called_once_with("sess-1")
    assert mock_append.call_count == 2
    calls = [c.args for c in mock_append.call_args_list]
    assert calls[0] == ("sess-1", "user", "hi")
    assert calls[1] == ("sess-1", "assistant", "Got it!")
