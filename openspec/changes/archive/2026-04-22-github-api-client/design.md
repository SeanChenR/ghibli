## Context

`github_api.py` 是整個 ghibli 工具鏈的 HTTP 執行層，位於 Gemini Function Calling 與 GitHub REST API 之間。Gemini 決定呼叫哪個工具後，只回傳 `tool_name`（字串）與 `args`（dict）；此模組負責把這兩個值轉成實際的 HTTP 請求並回傳原始 JSON 結果。

目前支援 6 個工具，對應到 GitHub REST API 的公開端點。認證為選用（`GITHUB_TOKEN` 環境變數），無 token 時走未認證請求（rate limit 60 req/hr）。

## Goals / Non-Goals

**Goals:**

- 將 `tool_name` + `args` 映射到正確的 GitHub REST API endpoint 與 HTTP method
- 自動從 `args` 抽出路徑參數（如 `owner`、`repo`），剩餘的作為 query params
- 統一的例外介面：呼叫端只需處理 `ToolCallError`（工具名稱錯誤）與 `GitHubAPIError`（HTTP/網路錯誤）
- 支援選用的 Bearer token 認證

**Non-Goals:**

- 不處理分頁 — 由後續 change 負責
- 不快取或重試 — 單純的一次性 HTTP 請求
- 不格式化輸出 — 屬於 `output-formatter` change

## Decisions

### 靜態 `_TOOL_MAP` 字典而非動態路由

以 `_TOOL_MAP: dict[str, tuple[str, str]]` 明確列出所有支援的工具（method, endpoint template），而非用 convention-based 方式動態產生 endpoint。

**理由**：工具集合固定（6 個），每個工具的 method 與 endpoint 都不同，靜態映射讓合法工具一目瞭然，未知工具立即被 `ToolCallError` 捕捉，不會有 silent failure。

**捨棄方案**：用函式名稱 convention 動態對應 endpoint — 靈活性過高，容易引入未預期的 tool name 被默默接受。

### Regex 抽取路徑參數

用 `re.compile(r"\{(\w+)\}")` 從 endpoint template 抽出路徑參數名稱（如 `{owner}`、`{repo}`），再從 `args` dict 中 `pop` 出對應值填入 URL；剩餘的 `args` 作為 query params 傳給 httpx。

**理由**：路徑參數與 query params 來自同一個 `args` dict（Gemini Function Calling 的輸出格式），必須在建 URL 時區分兩者。Regex 方式與 endpoint template 格式一致，不需要額外的 metadata。

**捨棄方案**：在 `_TOOL_MAP` 中額外列出每個工具的路徑參數名稱 — 重複資訊，維護兩份更容易出錯。

### 例外映射策略

- `httpx.HTTPStatusError`（4xx/5xx）→ `GitHubAPIError(message, status_code=N)`：保留 HTTP status code 供上層決策（如 403 rate limit vs 404 not found）
- `httpx.TimeoutException` → `GitHubAPIError("GitHub API request timeout", status_code=408)`：統一為 408，讓呼叫端不需要 import httpx 就能處理 timeout
- 未知 tool_name → `ToolCallError`：在查 `_TOOL_MAP` 時立即拋出，不等到 HTTP 呼叫

**理由**：呼叫端（agent loop）只需要處理 `GhibliError` 的子類別，不需要知道底層是 httpx 還是 requests。

## Risks / Trade-offs

- **無 token 時 rate limit 極低（60 req/hr）** → 建議使用者設定 `GITHUB_TOKEN`；錯誤訊息中含 status_code=403 可提示上層顯示提示
- **`args` dict 被 `pop` 修改** → `execute()` 接到的是 Gemini 回傳的 dict，目前呼叫端不重用這個 dict，可接受；若未來需要保留原始 args，改為 `dict(args)` copy 即可（已在實作中採用 `remaining_args = dict(args)`）
- **httpx 同步模式** → 目前 CLI 是同步的，使用 `httpx.request()`（非 async）。若未來改為 async agent loop，需換成 `httpx.AsyncClient`

## Open Questions

（無）
