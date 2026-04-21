## Why

對話 loop 每輪的 user/assistant 對話需要持久化，這樣使用者才能用 `--session <id>` 載入歷史並繼續對話，未來 Phase 3 多模型評測也需要以 SQL 查詢跨 session 的 tool call 記錄。目前 `src/ghibli/sessions.py` 是空模組。此 change 在 `sessions.py` 實作 SQLite session 的建立、讀取、更新操作。

## What Changes

- 在 `src/ghibli/sessions.py` 實作 Session 的 CRUD 操作，資料庫位於 `~/.ghibli/sessions.db`
- 建立兩張資料表：`sessions(id TEXT PRIMARY KEY, created_at TEXT, updated_at TEXT, title TEXT)` 與 `turns(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, role TEXT, content_json TEXT, tool_name TEXT, tool_args_json TEXT, tool_result_json TEXT, created_at TEXT)`
- 公開 API：`create_session() -> str`（回傳新 session id）、`get_session(session_id: str) -> dict | None`、`list_all_sessions() -> list[dict]`、`append_turn(session_id: str, role: str, content: str, tool_name: str | None, tool_args: dict | None, tool_result: dict | None) -> None`、`get_turns(session_id: str) -> list[dict]`
- 資料庫目錄 `~/.ghibli/` 在首次使用時自動建立

## Non-Goals

- 不實作 session 刪除（Phase 2 強化）
- 不實作 session 搜尋（Phase 3）
- 不暴露 SQL 查詢介面（Phase 3 透過直接連線資料庫）

## Capabilities

### New Capabilities

- `session-storage`: SQLite 的 session 建立、讀取、turn 追加、listing 能力；資料庫位於 `~/.ghibli/sessions.db`

### Modified Capabilities

（無）

## Impact

- 修改：`src/ghibli/sessions.py`
- 新增：`tests/unit/test_sessions.py`
- 依賴：`project-scaffold`（例外類別 `SessionError`）
