## Why

Gemini Function Calling 需要一組事先定義好的工具描述，才能在對話過程中自行決定要呼叫哪個 GitHub API 操作。目前 `src/ghibli/tools.py` 是空模組。此 change 在 `tools.py` 定義 6 個 GitHub API 工具（Python callable + Gemini schema），並在 `src/ghibli/agent.py` 實作 `chat()` 函式，以 Gemini `gemini-2.5-flash` 模型執行多輪 Function Calling 對話 loop。

## What Changes

- 在 `src/ghibli/tools.py` 以 Python `def` 定義 6 個工具函式：`search_repositories`、`get_repository`、`list_issues`、`list_pull_requests`、`get_user`、`list_releases`；每個函式的 docstring 與型別標注構成 Gemini function declaration schema
- 每個工具函式內部呼叫 `github_api.execute(tool_name, args)`，將 Gemini 傳入的 args 轉為 API 請求
- 建立 `src/ghibli/agent.py`，實作 `chat(user_message: str, session_id: str, json_output: bool) -> str` 函式：初始化 `google.genai.Client`（支援 API Key 或 Vertex AI 認證），呼叫 `client.models.generate_content()` 並傳入工具列表，執行 Function Calling loop 直到 Gemini 回傳純文字，最後回傳 Gemini 的文字回應
- 支援兩種 Gemini 認證方式：優先使用 `GEMINI_API_KEY`；若未設定則使用 Vertex AI（`VERTEX_PROJECT` + `VERTEX_LOCATION` + ADC）

## Non-Goals

- 不支援 Phase 3 多模型評測（LiteLLM 整合）
- 不實作 session history 的跨輪載入（屬於 `session-manager` change）
- 不格式化輸出（屬於 `output-formatter` change）

## Capabilities

### New Capabilities

- `gemini-function-calling`: 以 Gemini `gemini-2.5-flash` 執行多輪 Function Calling 對話，將 GitHub API 工具定義傳入並執行
- `github-tool-definitions`: 6 個 GitHub API 操作的 Python callable 定義（`search_repositories`、`get_repository`、`list_issues`、`list_pull_requests`、`get_user`、`list_releases`）
- `gemini-authentication`: 支援 `GEMINI_API_KEY`（API Key 模式）與 `VERTEX_PROJECT` + `VERTEX_LOCATION`（Vertex AI 模式）二擇一認證

### Modified Capabilities

（無）

## Impact

- 修改：`src/ghibli/tools.py`
- 新增：`src/ghibli/agent.py`、`tests/unit/test_tools.py`、`tests/unit/test_agent.py`
- 依賴：`project-scaffold`（例外類別）、`github-api-client`（`execute()` 函式）
