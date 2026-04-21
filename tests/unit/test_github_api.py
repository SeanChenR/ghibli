from unittest.mock import MagicMock, patch

import httpx
import pytest

from ghibli.exceptions import GitHubAPIError, ToolCallError
from ghibli.github_api import execute


def _mock_response(status_code: int = 200, json_data: dict | list | None = None):
    mock = MagicMock(spec=httpx.Response)
    mock.status_code = status_code
    mock.json.return_value = json_data if json_data is not None else {}
    if status_code >= 400:
        mock.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=mock,
        )
    else:
        mock.raise_for_status.return_value = None
    return mock


# --- 1.1: search_repositories returns parsed dict ---

def test_search_repositories_returns_parsed_dict():
    payload = {"total_count": 1, "items": []}
    with patch("httpx.request", return_value=_mock_response(200, payload)) as mock_req:
        result = execute("search_repositories", {"q": "python"})
    assert isinstance(result, dict)
    assert result == payload


# --- 1.2: get_repository substitutes path params ---

def test_get_repository_substitutes_path_params():
    with patch("httpx.request", return_value=_mock_response(200, {})) as mock_req:
        execute("get_repository", {"owner": "torvalds", "repo": "linux"})
    call_args, call_kwargs = mock_req.call_args
    assert call_args[1] == "https://api.github.com/repos/torvalds/linux"
    params = call_kwargs.get("params", {})
    assert "owner" not in params
    assert "repo" not in params


# --- 1.3: unknown tool raises ToolCallError ---

def test_unknown_tool_raises_tool_call_error():
    with pytest.raises(ToolCallError) as exc_info:
        execute("delete_everything", {})
    assert "delete_everything" in str(exc_info.value)


# --- 1.4: GITHUB_TOKEN auth header ---

def test_token_adds_authorization_header(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "test_token")
    with patch("httpx.request", return_value=_mock_response(200, {})) as mock_req:
        execute("search_repositories", {"q": "python"})
    _, call_kwargs = mock_req.call_args
    headers = call_kwargs.get("headers", {})
    assert headers.get("Authorization") == "Bearer test_token"


def test_no_token_no_auth_header(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch("httpx.request", return_value=_mock_response(200, {})) as mock_req:
        execute("search_repositories", {"q": "python"})
    _, call_kwargs = mock_req.call_args
    headers = call_kwargs.get("headers", {})
    assert "Authorization" not in headers


# --- 1.5: User-Agent always present ---

def test_user_agent_always_present(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch("httpx.request", return_value=_mock_response(200, {})) as mock_req:
        execute("search_repositories", {"q": "python"})
    _, call_kwargs = mock_req.call_args
    headers = call_kwargs.get("headers", {})
    assert headers.get("User-Agent") == "ghibli/0.1.0"


# --- 1.6: 4xx/5xx raises GitHubAPIError ---

def test_404_raises_github_api_error():
    with patch("httpx.request", return_value=_mock_response(404)):
        with pytest.raises(GitHubAPIError) as exc_info:
            execute("get_repository", {"owner": "no", "repo": "such"})
    assert exc_info.value.status_code == 404


def test_500_raises_github_api_error():
    with patch("httpx.request", return_value=_mock_response(500)):
        with pytest.raises(GitHubAPIError) as exc_info:
            execute("search_repositories", {"q": "python"})
    assert exc_info.value.status_code == 500


# --- 1.7: timeout raises GitHubAPIError ---

def test_timeout_raises_github_api_error():
    with patch("httpx.request", side_effect=httpx.TimeoutException("timed out")):
        with pytest.raises(GitHubAPIError) as exc_info:
            execute("search_repositories", {"q": "python"})
    assert "timeout" in str(exc_info.value).lower()
