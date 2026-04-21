import re

import pytest

from ghibli.sessions import (
    append_turn,
    create_session,
    get_session,
    get_turns,
    list_all_sessions,
)


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    import ghibli.sessions as sessions_module

    monkeypatch.setattr(sessions_module, "DB_PATH", tmp_path / "sessions.db")


# --- 1.1: DB initialisation ---

def test_database_initialized_on_first_use(tmp_path, monkeypatch):
    import ghibli.sessions as sessions_module

    db_path = tmp_path / "sessions.db"
    monkeypatch.setattr(sessions_module, "DB_PATH", db_path)
    list_all_sessions()
    assert db_path.exists()


# --- 1.2: create_session ---

def test_create_session_returns_uuid_string():
    result = create_session()
    assert isinstance(result, str)
    assert len(result) > 0
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", result)


def test_two_sessions_have_different_ids():
    id1 = create_session()
    id2 = create_session()
    assert id1 != id2


# --- 1.3: get_session ---

def test_get_session_returns_dict_for_existing():
    sid = create_session()
    result = get_session(sid)
    assert result is not None
    assert "id" in result
    assert "created_at" in result
    assert "updated_at" in result
    assert "title" in result
    assert result["id"] == sid


def test_get_session_returns_none_for_unknown():
    assert get_session("nonexistent-id") is None


# --- 1.4: list_all_sessions ---

def test_list_all_sessions_empty_db():
    assert list_all_sessions() == []


def test_list_all_sessions_returns_newest_first():
    id1 = create_session()
    id2 = create_session()
    sessions = list_all_sessions()
    assert len(sessions) == 2
    assert sessions[0]["created_at"] >= sessions[1]["created_at"]


# --- 1.5: append_turn user turn ---

def test_append_turn_stores_user_turn():
    sid = create_session()
    append_turn(sid, "user", "find python repos")
    turns = get_turns(sid)
    assert len(turns) == 1
    assert turns[0]["role"] == "user"
    assert "find python repos" in turns[0]["content_json"]


# --- 1.6: append_turn tool info ---

def test_append_turn_stores_tool_info():
    sid = create_session()
    append_turn(
        sid,
        "tool",
        "",
        tool_name="search_repositories",
        tool_args={"q": "python"},
        tool_result={"items": []},
    )
    turns = get_turns(sid)
    assert len(turns) == 1
    assert turns[0]["tool_name"] == "search_repositories"
    assert "python" in turns[0]["tool_args_json"]


# --- 1.7: get_turns ---

def test_get_turns_empty_for_new_session():
    sid = create_session()
    assert get_turns(sid) == []


def test_get_turns_returns_insertion_order():
    sid = create_session()
    append_turn(sid, "user", "first")
    append_turn(sid, "assistant", "second")
    turns = get_turns(sid)
    assert len(turns) == 2
    assert "first" in turns[0]["content_json"]
    assert "second" in turns[1]["content_json"]
