import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ghibli.exceptions import SessionError

DB_PATH: Path = Path.cwd() / ".ghibli" / "sessions.db"

_SESSIONS_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    title TEXT
);
"""

_TURNS_DDL = """
CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES sessions(id),
    role TEXT NOT NULL,
    content_json TEXT NOT NULL,
    tool_name TEXT,
    tool_args_json TEXT,
    tool_result_json TEXT,
    created_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_connection() -> sqlite3.Connection:
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute(_SESSIONS_DDL)
        conn.execute(_TURNS_DDL)
        conn.commit()
        return conn
    except sqlite3.Error as e:
        raise SessionError(str(e)) from e


def create_session() -> str:
    session_id = str(uuid.uuid4())
    now = _now()
    try:
        with _get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (id, created_at, updated_at, title)"
                " VALUES (?, ?, ?, ?)",
                (session_id, now, now, None),
            )
    except sqlite3.Error as e:
        raise SessionError(str(e)) from e
    return session_id


def get_session(session_id: str) -> dict | None:
    try:
        with _get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ?", (session_id,)
            ).fetchone()
    except sqlite3.Error as e:
        raise SessionError(str(e)) from e
    return dict(row) if row else None


def list_all_sessions() -> list[dict]:
    try:
        with _get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY created_at DESC"
            ).fetchall()
    except sqlite3.Error as e:
        raise SessionError(str(e)) from e
    return [dict(row) for row in rows]


def append_turn(
    session_id: str,
    role: str,
    content: str,
    tool_name: str | None = None,
    tool_args: dict | None = None,
    tool_result: dict | None = None,
) -> None:
    now = _now()
    try:
        with _get_connection() as conn:
            conn.execute(
                "INSERT INTO turns"
                " (session_id, role, content_json, tool_name,"
                "  tool_args_json, tool_result_json, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    session_id,
                    role,
                    json.dumps(content),
                    tool_name,
                    json.dumps(tool_args) if tool_args is not None else None,
                    json.dumps(tool_result) if tool_result is not None else None,
                    now,
                ),
            )
            conn.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now, session_id),
            )
    except sqlite3.Error as e:
        raise SessionError(str(e)) from e


def get_turns(session_id: str) -> list[dict]:
    try:
        with _get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM turns WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
    except sqlite3.Error as e:
        raise SessionError(str(e)) from e
    return [dict(row) for row in rows]


def count_turns(session_id: str) -> int:
    try:
        with _get_connection() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS n FROM turns WHERE session_id = ?",
                (session_id,),
            ).fetchone()
    except sqlite3.Error as e:
        raise SessionError(str(e)) from e
    return int(row["n"]) if row else 0


def delete_session(session_id: str) -> None:
    try:
        with _get_connection() as conn:
            conn.execute("DELETE FROM turns WHERE session_id = ?", (session_id,))
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    except sqlite3.Error as e:
        raise SessionError(str(e)) from e
