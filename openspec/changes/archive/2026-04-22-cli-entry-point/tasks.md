## 1. 測試（Red — 先寫，全部應失敗）

- [x] 1.1 [P] 在 `tests/unit/test_cli.py` 建立 Typer test client fixture：使用 `typer.testing.CliRunner`，建立 `runner` fixture；寫 `test_version_flag()` — invoke `app, ["--version"]`，斷言 exit_code == 0 且 output 含 `"ghibli"` 與版本號字串（對應：--version flag prints version and exits）
- [x] 1.2 [P] 在 `tests/unit/test_cli.py` 寫 `test_list_sessions_empty()` — invoke `app, ["--list-sessions"]`，斷言 exit_code == 0 且 output 含空狀態訊息（對應：--list-sessions with no sessions shows empty state）
- [x] 1.3 [P] 在 `tests/unit/test_cli.py` 寫 `test_json_flag_defaults_false()` — 以 `input="\n"` invoke `app, []`，斷言 exit_code == 0；寫 `test_json_flag_true_when_passed()` — 以 `input="\n"` invoke `app, ["--json"]`，斷言 exit_code == 0（對應：--json flag controls output format）
- [x] 1.4 [P] 在 `tests/unit/test_cli.py` 寫 `test_empty_line_exits_gracefully()` — 以 `input="\n"` invoke `app, []`，斷言 exit_code == 0 且 output 含告別訊息；寫 `test_eof_exits_gracefully()` — 以 `input=""` invoke `app, []`，斷言 exit_code == 0（對應：empty line ends the session、Ctrl+C or Ctrl+D ends the session gracefully）
- [x] 1.5 [P] 在 `tests/unit/test_cli.py` 寫 `test_unknown_session_id_rejected()` — invoke `app, ["--session", "nonexistent-id-xyz"]`，斷言 exit_code == 1 且 output 含錯誤訊息（對應：unknown session ID is rejected）

## 2. 實作（Green — 讓測試通過）

- [x] 2.1 在 `src/ghibli/cli.py` 宣告 Typer app 並實作 `--version` callback：使用 `typer.Option(callback=version_callback, is_eager=True)` 模式；callback 中印出 `f"ghibli {__version__}"` 並 `raise typer.Exit()`；從 `ghibli.__init__` import `__version__`（對應：--version flag prints version and exits）
- [x] 2.2 在 `src/ghibli/cli.py` 實作 `main()` 函式 signature：`def main(session: Annotated[Optional[str], typer.Option("--session", help="Resume a session by ID")] = None, list_sessions: Annotated[bool, typer.Option("--list-sessions")] = False, json_output: Annotated[bool, typer.Option("--json")] = False) -> None`（對應：所有 flag 宣告）
- [x] 2.3 在 `main()` 中實作 `--list-sessions` 分支：呼叫 `sessions.list_all_sessions()`（stub 回傳空列表 `[]`）；若列表為空，印出 `"No sessions found."`；否則以 `"{id}  {created_at}  {title}"` 格式印出每個 session；然後 `raise typer.Exit()`（對應：--list-sessions flag lists past sessions）
- [x] 2.4 在 `main()` 中實作 `--session` 載入：若 `session` 不為 None，呼叫 `sessions.get_session(session_id)`（stub 回傳 None）；若回傳 None，印出 `f"Error: session '{session}' not found"` 至 stderr 並 `raise typer.Exit(code=1)`；若 session 存在，以 `session_id = session` 繼續進入對話 loop，印出 `f"Resuming session {session_id}..."` 提示（對應：--session flag loads an existing session、unknown session ID is rejected）
- [x] 2.5 在 `main()` 中實作對話 loop：若 `session` 為 None，以 `session_id = sessions.create_session()`（stub 回傳 `"stub-session-id"`）建立新 session；進入 `while True` loop：以 `typer.prompt("You", prompt_suffix="> ")` 讀取輸入；空字串則印出 `"Bye!"` 並 break；捕捉 `KeyboardInterrupt` 與 `EOFError`，印出 `"\nBye!"` 並 break；否則印出 `f"[stub] {user_input}"` 佔位回應（對應：conversation loop starts on launch）

## 3. 驗證

- [x] 3.1 執行 `pytest tests/unit/test_cli.py -v` 確認全部測試通過（Green）
- [x] 3.2 手動執行 `ghibli --help`、`ghibli --version`、`ghibli --list-sessions`、`ghibli` 後輸入一行再空行退出，確認行為符合 spec
- [x] 3.3 執行 `ruff check src/ghibli/cli.py` 確認無 lint 錯誤
