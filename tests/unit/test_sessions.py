import re

import pytest

from ghibli.sessions import (
    append_turn,
    count_turns,
    create_session,
    delete_session,
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


# --- count_turns ---

def test_count_turns_zero_for_new_session():
    sid = create_session()
    assert count_turns(sid) == 0


def test_count_turns_reflects_appended_turns():
    sid = create_session()
    append_turn(sid, "user", "hello")
    append_turn(sid, "assistant", "hi")
    assert count_turns(sid) == 2


def test_count_turns_unknown_id_returns_zero():
    assert count_turns("does-not-exist") == 0


# --- delete_session ---

def test_delete_session_removes_empty_session():
    sid = create_session()
    delete_session(sid)
    assert get_session(sid) is None
    assert all(s["id"] != sid for s in list_all_sessions())


def test_delete_session_removes_session_and_turns():
    sid = create_session()
    append_turn(sid, "user", "q1")
    append_turn(sid, "assistant", "a1")
    append_turn(sid, "user", "q2")
    delete_session(sid)
    assert get_session(sid) is None
    assert get_turns(sid) == []


def test_delete_session_unknown_id_is_noop():
    # Should not raise
    delete_session("nonexistent-id")


# --- DB_PATH location (project-local .ghibli/sessions.db) ---


def test_db_path_points_to_cwd_ghibli_directory(tmp_path, monkeypatch):
    """DB_PATH SHALL resolve to <cwd>/.ghibli/sessions.db."""
    import ghibli.sessions as sessions_module
    import importlib

    monkeypatch.chdir(tmp_path)
    importlib.reload(sessions_module)
    try:
        assert sessions_module.DB_PATH == tmp_path / ".ghibli" / "sessions.db"
    finally:
        importlib.reload(sessions_module)  # restore module-level DB_PATH


def test_ghibli_dir_autocreated_on_first_db_use(tmp_path, monkeypatch):
    """`.ghibli/` SHALL be created automatically when a sessions function is first called."""
    import ghibli.sessions as sessions_module

    monkeypatch.setattr(sessions_module, "DB_PATH", tmp_path / ".ghibli" / "sessions.db")
    assert not (tmp_path / ".ghibli").exists()

    sessions_module.list_all_sessions()

    assert (tmp_path / ".ghibli").is_dir()
    assert (tmp_path / ".ghibli" / "sessions.db").exists()
