## Why

`project-scaffold` 建立了骨架，但 `src/ghibli/cli.py` 目前只有空的 Typer app。此 change 實作 CLI 的互動對話層：啟動一個持續的對話 loop，讓使用者多輪輸入自然語言，Gemini 透過 Function Calling 自行決定是否呼叫 GitHub API，並將每輪對話持久化至 SQLite session。

## What Changes

- 在 `src/ghibli/cli.py` 實作主指令 `main()`（無位置參數），啟動互動式對話 loop
- 支援 `--session <id>` 選項：載入已存在的 session 繼續對話
- 支援 `--list-sessions` flag：列出過去所有 session 後退出
- 支援 `--json` flag（預設 False）：控制輸出格式（Rich 格式或原始 JSON）
- 支援 `--version` flag：印出版本號後退出
- 對話 loop 在每輪讀取使用者輸入，遇到空行或 `Ctrl+C` / `Ctrl+D` 時結束 session
- 每輪對話呼叫 `agent.chat(message, session_id, json_output)` 並顯示回應（agent 整合在後續 change 完成）

## Non-Goals

- 不實作 Gemini API 呼叫或 Function Calling 邏輯 — 屬於 `github-tools` change
- 不實作 GitHub API 執行 — 屬於 `github-api-client` change
- 不實作 SQLite session 讀寫 — 屬於 `session-manager` change
- 不實作 Rich 格式化輸出 — 屬於 `output-formatter` change
- 此 change 的 `main()` 在 agent/session 模組就緒前，僅以 stub 回應呼叫

## Capabilities

### New Capabilities

- `cli-interface`: 互動對話 CLI 層——對話 loop、session 載入/建立、`--session`、`--list-sessions`、`--json`、`--version` flags、`Ctrl+C`/`Ctrl+D` 優雅結束

### Modified Capabilities

（無）

## Impact

- 修改：`src/ghibli/cli.py`
- 新增：`tests/unit/test_cli.py`
- 依賴：`project-scaffold`（pyproject.toml entry point 已設定）
- 後續整合：`session-manager`（session CRUD）、`github-tools` + `github-api-client`（agent loop）
