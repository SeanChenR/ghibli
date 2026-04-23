## MODIFIED Requirements

### Requirement: SQLite database initialized at project-local `.ghibli/sessions.db`

The module `src/ghibli/sessions.py` SHALL connect to `<cwd>/.ghibli/sessions.db` on first use (where `<cwd>` is the directory from which `ghibli` is invoked) and create the `.ghibli/` directory and the database file if they do not exist. The schema SHALL contain two tables:

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

Any `sqlite3` error during database operations SHALL be caught and re-raised as `SessionError`. The previous location at `~/.ghibli/sessions.db` is no longer used and SHALL NOT be read or written.

#### Scenario: Database and directory created under the current working directory

- **WHEN** any sessions function is called from a working directory where `./.ghibli/sessions.db` does not exist
- **THEN** the directory `./.ghibli/` is created and the database is initialized with both tables

#### Scenario: Home directory session db is not touched

- **WHEN** `~/.ghibli/sessions.db` exists from a previous install but the CLI is run from a different directory
- **THEN** `~/.ghibli/sessions.db` is neither read nor modified; only `./.ghibli/sessions.db` is used

#### Scenario: sqlite3 error raises SessionError

- **WHEN** a database operation fails (e.g., corrupted database)
- **THEN** `SessionError` is raised with the original error message

## ADDED Requirements

### Requirement: count_turns returns the number of turns for a session

The function `count_turns(session_id: str) -> int` in `src/ghibli/sessions.py` SHALL return the number of rows in the `turns` table whose `session_id` matches. When the session has no turns, the function SHALL return 0. When the `session_id` does not match any row, the function SHALL also return 0 (treat as empty, not an error).

#### Scenario: count_turns returns 0 immediately after create_session

- **WHEN** a new session is created and `count_turns(session_id)` is called before any `append_turn`
- **THEN** the function returns 0

#### Scenario: count_turns returns number of appended turns

- **WHEN** two `append_turn(session_id, ...)` calls are made and then `count_turns(session_id)` is called
- **THEN** the function returns 2

#### Scenario: count_turns on unknown session id returns 0

- **WHEN** `count_turns("nonexistent-id")` is called
- **THEN** the function returns 0 without raising

### Requirement: delete_session removes a session row and all its turns

The function `delete_session(session_id: str) -> None` in `src/ghibli/sessions.py` SHALL delete the matching row from the `sessions` table and all rows from the `turns` table whose `session_id` matches. When the `session_id` does not exist, the function SHALL be a no-op (no exception raised). `sqlite3` errors SHALL be wrapped as `SessionError`, consistent with other functions in this module.

#### Scenario: delete_session removes an empty session

- **WHEN** `create_session()` returns id X, no turns are added, and `delete_session(X)` is called
- **THEN** `get_session(X)` returns `None` and `list_all_sessions()` does not include X

#### Scenario: delete_session removes session with existing turns

- **WHEN** a session X has 3 appended turns and `delete_session(X)` is called
- **THEN** `get_session(X)` returns `None` and `get_turns(X)` returns `[]`

#### Scenario: delete_session on unknown id is a no-op

- **WHEN** `delete_session("does-not-exist")` is called on an empty or unrelated database
- **THEN** the function returns without raising

### Requirement: last_model file read and write

The picker module SHALL persist the user's most recent model selection to `<cwd>/.ghibli/last_model` as a plain-text file containing a single line with the model identifier followed by `\n`. Two operations are required:

- `read_last_model() -> str | None` SHALL return the file contents stripped of trailing whitespace when the file exists and is non-empty; otherwise return `None`.
- `write_last_model(identifier: str) -> None` SHALL create the parent `.ghibli/` directory if missing, then write the file as `<identifier>\n` with UTF-8 encoding, replacing any previous content.

Neither operation SHALL raise on missing-file for read; write SHALL raise through standard OS errors if the directory cannot be created.

#### Scenario: read_last_model returns None when the file is absent

- **WHEN** `<cwd>/.ghibli/last_model` does not exist
- **THEN** `read_last_model()` returns `None`

#### Scenario: write then read round-trips the identifier

- **WHEN** `write_last_model("openai:gpt-4o-mini")` is called followed by `read_last_model()`
- **THEN** the second call returns the string `"openai:gpt-4o-mini"` (no trailing newline)

#### Scenario: write_last_model creates the .ghibli directory

- **WHEN** `<cwd>/.ghibli/` does not exist and `write_last_model("openai:gpt-4o-mini")` is called
- **THEN** the directory `<cwd>/.ghibli/` is created and the file `last_model` inside it contains exactly `openai:gpt-4o-mini\n`
