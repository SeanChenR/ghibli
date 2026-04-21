## Why

Gemini Function Calling 在決定呼叫 GitHub 工具時，會回傳一個 `tool_name`（如 `search_repositories`）與 `args`（如 `{"q": "python", "per_page": 5}`）。此 change 實作 GitHub REST API 的執行層：接收 `tool_name` 與 `args`，將其映射到對應的 `api.github.com` 端點，執行 HTTP 請求，並回傳原始 API 回應資料。

## What Changes

- 在 `src/ghibli/github_api.py` 實作 `execute(tool_name: str, args: dict) -> dict | list` 函式
- 維護一個內部映射表（`_TOOL_MAP`），將 6 個工具名稱映射到對應的端點 template 與 HTTP method
- 使用 `httpx` 發送 HTTP 請求至 GitHub REST API（base URL: `https://api.github.com`）
- 從環境變數 `GITHUB_TOKEN` 讀取 PAT（選用）；有 token 時加入 `Authorization: Bearer` header
- 對 4xx/5xx 回應 raise `GitHubAPIError`，並附上 HTTP status code
- 對未知的 `tool_name` raise `ToolCallError`
- 設定請求 timeout 為 10 秒；timeout 時 raise `GitHubAPIError`

## Non-Goals

- 不處理 GitHub GraphQL API — 只支援 REST API
- 不實作分頁（pagination）— 屬於後續強化 change
- 不快取 API 回應
- 不格式化輸出 — 屬於 `output-formatter` change

## Capabilities

### New Capabilities

- `github-api-execution`: 接收 Gemini Function Calling 回傳的 `tool_name` 與 `args`，執行對應的 GitHub REST API 請求並回傳原始 JSON 資料

### Modified Capabilities

（無）

## Impact

- 修改：`src/ghibli/github_api.py`
- 新增：`tests/unit/test_github_api.py`、`tests/integration/test_github_api_integration.py`
- 依賴：`project-scaffold`（例外類別 `GitHubAPIError`、`ToolCallError`）、`github-tools`（定義 6 個工具名稱）
