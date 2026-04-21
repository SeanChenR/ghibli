## 1. 測試（Red — 先寫，全部應失敗）

- [x] 1.1 在 `tests/unit/test_sessions.py` 建立 `tmp_db` fixture：使用 `tmp_path` 建立暫時資料庫路徑，monkeypatch `ghibli.sessions.DB_PATH` 指向 `tmp_path / "sessions.db"`，確保測試互相隔離；寫 `test_database_initialized_on_first_use()` — 呼叫 `list_all_sessions()`，斷言 tmp_path 下的 `sessions.db` 檔案存在（對應：SQLite database initialized at ~/.ghibli/sessions.db）
- [x] 1.2 [P] 在 `tests/unit/test_sessions.py` 寫 `test_create_session_returns_uuid_string()` — 呼叫 `create_session()`，斷言回傳值為非空字串且符合 UUID4 格式（`re.match(r'^[0-9a-f-]{36}$', result)`）；寫 `test_two_sessions_have_different_ids()` — 呼叫兩次 `create_session()`，斷言兩個 ID 不同（對應：create_session returns a new unique session ID）
- [x] 1.3 [P] 在 `tests/unit/test_sessions.py` 寫 `test_get_session_returns_dict_for_existing()` — `create_session()` 後以 id 呼叫 `get_session(id)`，斷言回傳值含 `"id"`, `"created_at"`, `"updated_at"`, `"title"` key；寫 `test_get_session_returns_none_for_unknown()` — 以 `"nonexistent"` 呼叫，斷言回傳 None（對應：get_session returns session dict or None）
- [x] 1.4 [P] 在 `tests/unit/test_sessions.py` 寫 `test_list_all_sessions_empty_db()` — 在空 db 呼叫，斷言回傳 `[]`；寫 `test_list_all_sessions_returns_newest_first()` — 建立兩個 session 後，斷言第一個回傳的 `created_at` ≥ 第二個（對應：list_all_sessions returns all sessions ordered by created_at descending）
- [x] 1.5 [P] 在 `tests/unit/test_sessions.py` 寫 `test_append_turn_stores_user_turn()` — `create_session()` 後 `append_turn(id, "user", "find python repos")`，再呼叫 `get_turns(id)`，斷言列表長度為 1 且 `turns[0]["role"] == "user"` 且 content_json 含 `"find python repos"`（對應：append_turn persists a conversation turn）
- [x] 1.6 [P] 在 `tests/unit/test_sessions.py` 寫 `test_append_turn_stores_tool_info()` — `append_turn(id, "tool", "", tool_name="search_repositories", tool_args={"q": "python"}, tool_result={"items": []})`，取回 turns 斷言 `tool_name == "search_repositories"` 且 tool_args_json 含 `"python"`（對應：append_turn stores tool_name and args）
- [x] 1.7 [P] 在 `tests/unit/test_sessions.py` 寫 `test_get_turns_empty_for_new_session()` — 新 session 無 turns，斷言 `get_turns(id) == []`；寫 `test_get_turns_returns_insertion_order()` — append 兩個 turn 後，斷言順序正確（對應：get_turns returns all turns for a session ordered by id ascending）

## 2. 實作（Green）

- [x] 2.1 在 `src/ghibli/sessions.py` 定義 `DB_PATH: Path = Path.home() / ".ghibli" / "sessions.db"`；實作 `_get_connection() -> sqlite3.Connection`：確保 `DB_PATH.parent` 存在（`DB_PATH.parent.mkdir(parents=True, exist_ok=True)`），以 `sqlite3.connect(DB_PATH)` 取得連線，執行 `CREATE TABLE IF NOT EXISTS` 建立 `sessions` 與 `turns` 兩張表；以 `try/except sqlite3.Error` 包裹，捕捉時 raise `SessionError(str(e))`（對應：SQLite database initialized at ~/.ghibli/sessions.db）
- [x] 2.2 在 `src/ghibli/sessions.py` 實作 `create_session() -> str`：生成 `session_id = str(uuid.uuid4())`，以 `now = datetime.utcnow().isoformat()` 取得時間，INSERT 新 row 至 sessions；以 `try/except sqlite3.Error` 包裹，捕捉時 raise `SessionError(str(e))`；return `session_id`（對應：create_session returns a new unique session ID）
- [x] 2.3 在 `src/ghibli/sessions.py` 實作 `get_session(session_id: str) -> dict | None`：SELECT from sessions WHERE id = ?；若無結果回傳 None；否則回傳 dict（對應：get_session returns session dict or None）
- [x] 2.4 在 `src/ghibli/sessions.py` 實作 `list_all_sessions() -> list[dict]`：SELECT * FROM sessions ORDER BY created_at DESC；回傳 list of dict（對應：list_all_sessions returns all sessions ordered by created_at descending）
- [x] 2.5 在 `src/ghibli/sessions.py` 實作 `append_turn()` 與 `get_turns()`：`append_turn` INSERT 至 turns 並 UPDATE sessions.updated_at；`get_turns` SELECT * FROM turns WHERE session_id = ? ORDER BY id ASC，回傳 list of dict；皆以 `try/except sqlite3.Error` 包裹 raise `SessionError`（對應：append_turn persists a conversation turn、get_turns returns all turns for a session ordered by id ascending）

## 3. 驗證

- [x] 3.1 執行 `pytest tests/unit/test_sessions.py -v` 確認全部測試通過（Green）
- [x] 3.2 執行 `ruff check src/ghibli/sessions.py` 確認無 lint 錯誤
