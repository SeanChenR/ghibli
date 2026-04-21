## Why

CLI 能接收使用者輸入後，需要將自然語言查詢轉換成可執行的 GitHub REST API 請求參數。此 change 實作核心的意圖解析層：呼叫 Gemini API，將自然語言解析成結構化的 `GitHubIntent`（endpoint + params），讓後續的 API 執行層有確定的資料結構可依賴。輸出 schema 的穩定性在此確立，Phase 3 的 ground truth 標注依賴於此。

## What Changes

- 在 `src/ghibli/intent.py` 定義 `GitHubIntent` dataclass（`endpoint: str`、`method: str`、`params: dict[str, str]`、`description: str`）
- 在 `src/ghibli/intent.py` 實作 `parse_intent(query: str) -> GitHubIntent` 函式，呼叫 Gemini API 並解析回應
- Gemini API 呼叫使用結構化輸出（JSON mode）確保輸出 schema 穩定
- 當 Gemini API 無法解析意圖時，raise `IntentParseError`
- 支援兩種 Gemini 認證方式：
  - **API Key 模式**：從環境變數 `GEMINI_API_KEY` 讀取，使用 `genai.Client(api_key=...)`
  - **Vertex AI 模式**：從環境變數 `VERTEX_PROJECT`（必要）與 `VERTEX_LOCATION`（選用，預設 `us-central1`）讀取，使用 `genai.Client(vertexai=True, project=..., location=...)` 搭配 Google Application Default Credentials（ADC）
- 認證優先順序：`GEMINI_API_KEY` 優先；若未設定則嘗試 Vertex AI；兩者皆未設定時 raise `IntentParseError`

## Non-Goals

- 不處理 Phase 2 的 typo 容錯、多語言支援、模糊查詢 fallback — 屬於 `input-hardening` change
- 不執行 GitHub API — 屬於 `github-api-client` change
- 不支援 LiteLLM 多模型 — 屬於 Phase 3

## Capabilities

### New Capabilities

- `intent-parsing`: 自然語言 → `GitHubIntent` 結構化資料（endpoint、method、params、description）的解析能力，透過 Gemini 2.5 Flash API；支援 API Key 與 Vertex AI 兩種認證方式

### Modified Capabilities

（無）

## Impact

- 修改：`src/ghibli/intent.py`
- 新增：`tests/unit/test_intent.py`、`tests/integration/test_intent_integration.py`
- 依賴：`project-scaffold`（例外類別）、至少一種認證方式（`GEMINI_API_KEY` 或 `VERTEX_PROJECT` + ADC）
- 注意：`GitHubIntent` 的 schema（欄位名稱與型別）在此 change 後凍結，不可在後續 change 中更改欄位名稱
