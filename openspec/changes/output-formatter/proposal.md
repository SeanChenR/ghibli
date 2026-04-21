## Why

Gemini 在完成 Function Calling 之後，會回傳一個自然語言回應文字（text response），其中可能包含對 GitHub API 結果的摘要或說明。此 change 實作輸出層：將 Gemini 的文字回應以 Rich Markdown 格式渲染（預設），或以原始 JSON 字串輸出（`--json` flag），並串接 `cli.py` 的對話 loop 形成完整的端到端流程。

## What Changes

- 在 `src/ghibli/output.py` 實作 `render_text(text: str, json_output: bool) -> None` 函式
- 當 `json_output=False` 時，使用 `rich.console.Console().print(rich.markdown.Markdown(text))` 渲染 Markdown
- 當 `json_output=True` 時，以 `json.dumps({"response": text}, indent=2, ensure_ascii=False)` 輸出原始 JSON
- 當 `text` 為空字串時，印出 `"(no response)"` 並 return
- 串接 `cli.py` 中的對話 loop：每輪呼叫 `agent.chat()` 後以 `render_text()` 顯示回應

## Non-Goals

- 不直接渲染 GitHub API 原始 JSON 表格（由 Gemini 負責摘要，render 只處理文字）
- 不支援自訂欄位過濾（Phase 2 強化）
- 不支援分頁顯示（Phase 2 強化）

## Capabilities

### New Capabilities

- `output-rendering`: 將 Gemini 文字回應格式化為 Rich Markdown 或 JSON 字串的輸出能力

### Modified Capabilities

（無）

## Impact

- 修改：`src/ghibli/output.py`、`src/ghibli/cli.py`（替換 stub 輸出，串接完整 pipeline）
- 新增：`tests/unit/test_output.py`
- 依賴：`cli-entry-point`、`github-tools`、`github-api-client`、`session-manager`
