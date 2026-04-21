## Context

這個 change 是 ghibli 的核心 AI 層，連接使用者的自然語言輸入與 GitHub REST API：

- `tools.py`：定義 6 個 Python callable，作為 Gemini Function Calling 的工具宣告
- `agent.py`：`chat()` 函式，初始化 Gemini 客戶端、執行多輪 Function Calling loop，直到 Gemini 回傳純文字回應

`cli.py` 在此 change 完成後可以把 `[stub]` 替換成 `agent.chat()` 呼叫。

## Goals / Non-Goals

**Goals:**

- 讓 Gemini 能夠自行決定呼叫哪個 GitHub 工具（Function Calling）
- 支援多輪 Function Calling（一次對話可能觸發多個連續工具呼叫）
- 雙認證模式：`GEMINI_API_KEY`（優先）或 Vertex AI（`VERTEX_PROJECT`）
- 統一例外介面：工具執行錯誤一律包裝為 `ToolCallError`

**Non-Goals:**

- 不整合 session history（屬於 `session-manager` change）
- 不格式化輸出（屬於 `output-formatter` change）
- 不支援 Phase 3 多模型評測（LiteLLM）

## Decisions

### Python callable 作為 Gemini 工具宣告而非手動 JSON schema

直接把 Python 函式（有型別標注和 docstring）傳入 `tools=[...]`，由 `google-genai` SDK 自動從函式簽名產生 Function Declaration schema，而非手動維護 JSON schema。

**理由：** `google-genai` SDK 支援從 Python 函式自動推導 schema，開發者只需維護 Python 函式的型別和文件，不需要同步維護另一份 JSON schema，消除兩份資料不一致的風險。

**捨棄方案：** 手動定義 `types.FunctionDeclaration` — schema 與實作分離，容易脫節。

### `locals()` 收集參數傳入 `execute()`

工具函式以 `{k: v for k, v in locals().items() if v is not None}` 從函式 local scope 收集參數，傳給 `github_api.execute()`。

**理由：** 避免手動重複列出每個參數兩次（函式簽名一次、dict 建構一次）。`locals()` 在函式開頭呼叫時只包含函式參數，簡潔且不易出錯。

**捨棄方案：** 手動建 dict（`{"q": q, "sort": sort, ...}`）— 重複，參數更改時需修改兩處。

### `GEMINI_API_KEY` 優先於 Vertex AI，兩者都沒有時立即 raise

認證邏輯：有 `GEMINI_API_KEY` → API Key 模式；只有 `VERTEX_PROJECT` → Vertex AI 模式；兩者都沒有 → 立即 raise `ToolCallError`（在 `chat()` 呼叫時，而非 import 時）。

**理由：** 讓錯誤在使用時才出現（not at import time），錯誤訊息同時列出兩個環境變數名稱，使用者一目瞭然該設哪個。

**捨棄方案：** 模組 import 時驗證 → 會讓測試環境難以 mock，也讓 `--version` 等不需要 Gemini 的功能失敗。

### Function Calling loop 以 `response.function_calls` 判斷是否繼續

每次 `generate_content` 後，以 `if not response.function_calls` 判斷是否結束 loop；有 function calls 則執行工具、把 model turn + tool results 加回 `contents`，再次呼叫。

**理由：** `response.function_calls` 是 google-genai SDK 的標準屬性，空列表為 falsy，語意清晰。Gemini 決定何時停止呼叫工具，agent 只是執行並回傳結果。

## Risks / Trade-offs

- **[無限 loop 風險]** 若 Gemini 持續回傳 function calls 而不產生文字，loop 永遠不結束 → 目前沒有 iteration limit；Phase 2 可加入最大輪次保護
- **[Gemini schema 推導限制]** `google-genai` SDK 的自動 schema 推導對複雜型別有限制（e.g., union types、nested objects）→ 目前工具函式只用 `str` 和 `int`，無影響
- **[session_id 和 json_output 未使用]** `chat()` 簽名接受這兩個參數但不使用，預留給 `session-manager` 和 `output-formatter` 整合 → 明確記錄為預留，不會引起誤解

## Open Questions

（無）
