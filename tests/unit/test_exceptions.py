import pytest

from ghibli.exceptions import (
    GhibliError,
    GitHubAPIError,
    OutputError,
    SessionError,
    ToolCallError,
)


# --- GhibliError base class ---

def test_ghibli_error_is_exception():
    assert issubclass(GhibliError, Exception)


def test_any_subclass_catchable_as_ghibli_error():
    with pytest.raises(GhibliError):
        raise ToolCallError("x")


# --- ToolCallError ---

def test_tool_call_error_carries_message():
    err = ToolCallError("msg")
    assert "msg" in str(err)


def test_tool_call_error_is_ghibli_error():
    err = ToolCallError("fail")
    assert isinstance(err, GhibliError)


# --- GitHubAPIError ---

def test_github_api_error_exposes_status_code():
    err = GitHubAPIError("not found", status_code=404)
    assert err.status_code == 404


def test_github_api_error_is_ghibli_error():
    err = GitHubAPIError("forbidden", status_code=403)
    assert isinstance(err, GhibliError)


# --- SessionError ---

def test_session_error_is_ghibli_error():
    assert isinstance(SessionError("db error"), GhibliError)


# --- OutputError ---

def test_output_error_is_ghibli_error():
    assert isinstance(OutputError("render failed"), GhibliError)
