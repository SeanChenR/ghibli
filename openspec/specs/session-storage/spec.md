# session-storage Specification

## Purpose

TBD - created by archiving change 'session-manager'. Update Purpose after archive.

## Requirements

### Requirement: SQLite database initialized at ~/.ghibli/sessions.db

The module `src/ghibli/sessions.py` SHALL connect to `~/.ghibli/sessions.db` on first use and create the database file and directory if they do not exist. The schema SHALL contain two tables:

```sql
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    title TEXT
);

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
```

Any `sqlite3` error during database operations SHALL be caught and re-raised as `SessionError`.

#### Scenario: Database and directory created on first use

- **WHEN** any sessions function is called and `~/.ghibli/sessions.db` does not exist
- **THEN** `~/.ghibli/` is created and the database is initialized with both tables

#### Scenario: sqlite3 error raises SessionError

- **WHEN** a database operation fails (e.g., corrupted database)
- **THEN** `SessionError` is raised with the original error message


<!-- @trace
source: session-manager
updated: 2026-04-22
code:
  - .env.example
  - pyproject.toml
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
  - src/ghibli/output.py
  - src/ghibli/tools.py
  - tests/integration/__init__.py
  - uv.lock
  - src/ghibli/github_api.py
  - specs/mission.md
  - src/ghibli/cli.py
  - tests/unit/__init__.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/exceptions.py
  - specs/tech-stack.md
  - src/ghibli/sessions.py
  - CLAUDE.md
  - .spectra.yaml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_sessions.py
-->

---
### Requirement: create_session returns a new unique session ID

The function `create_session() -> str` SHALL insert a new row into `sessions` with a UUID4 id, the current UTC time as `created_at` and `updated_at`, and `title=None`. It SHALL return the new session ID as a string.

#### Scenario: create_session returns a non-empty string ID

- **WHEN** `create_session()` is called
- **THEN** it returns a non-empty string that is a valid UUID4

#### Scenario: Two consecutive calls return different IDs

- **WHEN** `create_session()` is called twice
- **THEN** both returned IDs are different strings


<!-- @trace
source: session-manager
updated: 2026-04-22
code:
  - .env.example
  - pyproject.toml
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
  - src/ghibli/output.py
  - src/ghibli/tools.py
  - tests/integration/__init__.py
  - uv.lock
  - src/ghibli/github_api.py
  - specs/mission.md
  - src/ghibli/cli.py
  - tests/unit/__init__.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/exceptions.py
  - specs/tech-stack.md
  - src/ghibli/sessions.py
  - CLAUDE.md
  - .spectra.yaml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_sessions.py
-->

---
### Requirement: get_session returns session dict or None

The function `get_session(session_id: str) -> dict | None` SHALL query `sessions` by primary key and return a dict with keys `id`, `created_at`, `updated_at`, `title` if found, or `None` if no row matches `session_id`.

#### Scenario: get_session returns dict for existing session

- **WHEN** `get_session(id)` is called with a valid session ID
- **THEN** returns a dict containing `"id"`, `"created_at"`, `"updated_at"`, `"title"` keys

#### Scenario: get_session returns None for unknown ID

- **WHEN** `get_session("nonexistent-id")` is called
- **THEN** returns `None`


<!-- @trace
source: session-manager
updated: 2026-04-22
code:
  - .env.example
  - pyproject.toml
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
  - src/ghibli/output.py
  - src/ghibli/tools.py
  - tests/integration/__init__.py
  - uv.lock
  - src/ghibli/github_api.py
  - specs/mission.md
  - src/ghibli/cli.py
  - tests/unit/__init__.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/exceptions.py
  - specs/tech-stack.md
  - src/ghibli/sessions.py
  - CLAUDE.md
  - .spectra.yaml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_sessions.py
-->

---
### Requirement: list_all_sessions returns all sessions ordered by created_at descending

The function `list_all_sessions() -> list[dict]` SHALL return all rows from `sessions` as a list of dicts, ordered by `created_at` descending (newest first). When no sessions exist, it SHALL return an empty list `[]`.

#### Scenario: list_all_sessions returns empty list when no sessions exist

- **WHEN** `list_all_sessions()` is called on an empty database
- **THEN** returns `[]`

#### Scenario: list_all_sessions returns sessions newest first

- **WHEN** multiple sessions exist
- **THEN** the returned list is ordered by `created_at` descending


<!-- @trace
source: session-manager
updated: 2026-04-22
code:
  - .env.example
  - pyproject.toml
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
  - src/ghibli/output.py
  - src/ghibli/tools.py
  - tests/integration/__init__.py
  - uv.lock
  - src/ghibli/github_api.py
  - specs/mission.md
  - src/ghibli/cli.py
  - tests/unit/__init__.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/exceptions.py
  - specs/tech-stack.md
  - src/ghibli/sessions.py
  - CLAUDE.md
  - .spectra.yaml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_sessions.py
-->

---
### Requirement: append_turn persists a conversation turn

The function `append_turn(session_id: str, role: str, content: str, tool_name: str | None = None, tool_args: dict | None = None, tool_result: dict | None = None) -> None` SHALL insert a row into `turns` with the provided values. `content` is stored as a JSON string `json.dumps(content)`. `tool_args` and `tool_result` are stored as `json.dumps(v)` when not None. `created_at` is the current UTC time. It SHALL also update `sessions.updated_at` to the current UTC time.

#### Scenario: append_turn stores user turn

- **WHEN** `append_turn(session_id, "user", "find python repos")` is called
- **THEN** a row exists in `turns` with `role="user"` and `content_json` containing `"find python repos"`

#### Scenario: append_turn stores tool_name and args

- **WHEN** `append_turn(session_id, "tool", "", tool_name="search_repositories", tool_args={"q": "python"}, tool_result={"items": []})` is called
- **THEN** a row exists in `turns` with `tool_name="search_repositories"` and `tool_args_json` containing `"python"`


<!-- @trace
source: session-manager
updated: 2026-04-22
code:
  - .env.example
  - pyproject.toml
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
  - src/ghibli/output.py
  - src/ghibli/tools.py
  - tests/integration/__init__.py
  - uv.lock
  - src/ghibli/github_api.py
  - specs/mission.md
  - src/ghibli/cli.py
  - tests/unit/__init__.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/exceptions.py
  - specs/tech-stack.md
  - src/ghibli/sessions.py
  - CLAUDE.md
  - .spectra.yaml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_sessions.py
-->

---
### Requirement: get_turns returns all turns for a session ordered by id ascending

The function `get_turns(session_id: str) -> list[dict]` SHALL return all rows from `turns` matching `session_id`, ordered by `id` ascending (insertion order). Each dict SHALL have keys: `id`, `session_id`, `role`, `content_json`, `tool_name`, `tool_args_json`, `tool_result_json`, `created_at`.

#### Scenario: get_turns returns empty list for session with no turns

- **WHEN** `get_turns(session_id)` is called on a newly created session
- **THEN** returns `[]`

#### Scenario: get_turns returns turns in insertion order

- **WHEN** two turns are appended and then `get_turns()` is called
- **THEN** the list contains exactly 2 dicts in the order they were appended

<!-- @trace
source: session-manager
updated: 2026-04-22
code:
  - .env.example
  - pyproject.toml
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
  - src/ghibli/output.py
  - src/ghibli/tools.py
  - tests/integration/__init__.py
  - uv.lock
  - src/ghibli/github_api.py
  - specs/mission.md
  - src/ghibli/cli.py
  - tests/unit/__init__.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/exceptions.py
  - specs/tech-stack.md
  - src/ghibli/sessions.py
  - CLAUDE.md
  - .spectra.yaml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_sessions.py
-->