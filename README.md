# ghibli — GitHub Intelligence Bridge

用自然語言查詢 GitHub，不需要記住 API 格式。

> **Take-Home Assessment 快速索引**
> - **Part 1 — 執行 CLI 工具**：`uv run ghibli`（詳見[使用方式](#使用方式)）
> - **Part 2 — 執行 Eval Pipeline**：`uv run python evals/run_evals.py`（詳見 [Eval 框架](#eval-框架part-2-入口)）
> - **架構決策與取捨**：見[架構決策與取捨](#架構決策與取捨)章節
> - **已知限制說明**：見[已知限制](#已知限制)章節

```
You> 搜尋最多星星的 TypeScript 前端框架
Ionic Framework 是最受歡迎的 TypeScript 前端框架，它有 52466 顆星。

You> 可以告訴我它的最新 release 嗎
Ionic Framework 最新版本是 v8.4.0，發布於 2025-03-12。
```

---

## 安裝

需要 Python 3.12+ 與 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/yourname/ghibli
cd ghibli
uv sync
```

複製並填寫環境變數：

```bash
cp .env.example .env
# 編輯 .env，填入 GEMINI_API_KEY
```

---

## 使用方式

```bash
uv run ghibli                        # 開新 session，進入對話
uv run ghibli --session <id>         # 接續歷史 session
uv run ghibli --list-sessions        # 列出所有 session
uv run ghibli --json                 # 輸出原始 JSON 而非 Rich Markdown
uv run ghibli --version              # 顯示版本
```

### 範例查詢

```
搜尋最多星星的 Python 機器學習 repo
torvalds 這個人是誰
列出 facebook/react 最近 10 個 open issue
microsoft/vscode 最新的 release 是哪一版
找一個用 Go 寫的高效能 HTTP server
```

---

## 環境變數

複製 `.env.example` 並填寫：

| 變數 | 必要 | 說明 |
|---|---|---|
| `GEMINI_API_KEY` | 二擇一 | Gemini API Key（[取得](https://aistudio.google.com/app/apikey)） |
| `GOOGLE_CLOUD_PROJECT` | 二擇一 | Vertex AI 專案 ID（搭配 Google ADC） |
| `GOOGLE_CLOUD_LOCATION` | 選用 | Vertex AI 區域，預設 `us-central1` |
| `GITHUB_TOKEN` | 選用 | GitHub PAT，未設定時每小時限 60 次請求 |

---

## 開發

```bash
# 執行測試（含覆蓋率報告）
uv run pytest

# Lint
uv run ruff check src/

# 格式化
uv run black src/ tests/
```

測試覆蓋率門檻：80%（由 `pyproject.toml` 強制執行）。

---

## 架構

```
自然語言輸入
     ↓
cli.py（Typer 對話 loop）
     ↓
agent.py（Gemini 2.5 Flash Function Calling）
     ↓  ← 載入/儲存 session history
sessions.py（SQLite ~/.ghibli/sessions.db）
     ↓
tools.py（6 個 GitHub tool function）
     ↓
github_api.py（httpx → GitHub REST API）
     ↓
output.py（Rich Markdown / JSON 輸出）
```

---

## 架構決策與取捨

### 為什麼用 Function Calling，而不是 prompt-based JSON 輸出？

最直觀的做法是要求 LLM 輸出一段 JSON（`{"tool": "search_repositories", "args": {...}}`），再由程式解析執行。我選擇不這樣做，原因有三：

1. **型別安全**：Function Calling 由 SDK 自動驗證參數型別與必填欄位，prompt-based 輸出需要自己寫 schema validation，且 LLM 容易偷偷漏欄位或型別錯誤。
2. **多步驟推理**：面對「找 star 最多的 Go web framework，再看它最近的 issue」這類查詢，Function Calling 允許模型在同一次對話中連續呼叫多個 tool，prompt-based 要自己實作 agentic loop。
3. **可觀測性**：`response.function_calls` 直接暴露模型呼叫了哪個 tool、帶了什麼參數，在 eval 框架中可以直接記錄 `tools_called`，不需要額外解析 LLM 輸出。

取捨：Function Calling 把控制權交給模型，偶爾模型會選錯 tool 或跳過必要步驟，需要 system prompt 補強。

### 為什麼用 SQLite 而不是 in-memory 儲存？

CLI 工具的使用情境是多次短暫啟動，每次對話幾輪後關閉。in-memory 儲存代表每次啟動都是全新 session，無法做到「接續上次問到哪裡」。

SQLite 選擇的理由：
- **零配置**：不需要起 server，單一檔案存在 `~/.ghibli/sessions.db`
- **足夠輕量**：對話歷史的資料量極小，SQLite 完全夠用
- **持久化**：允許 `--session <id>` 接續歷史對話

取捨：目前沒有 history truncation，長時間使用後 session 會無限增長。生產環境應加入 token 預算上限或滾動視窗機制。

### 為什麼停用 automatic_function_calling？

`google-genai` SDK 預設會自動執行 function call 並把結果回傳給模型，整個 agentic loop 在 SDK 內部完成，呼叫者看不到過程。

我選擇手動控制（`disable=True`）的原因：
- **可觀測**：eval 框架需要記錄哪些 tool 被呼叫；自動模式下無法 patch tool 函式並追蹤呼叫
- **錯誤邊界清楚**：每次 tool 呼叫都在我的 try/except 裡，GitHub API 錯誤可以正確包裝成 `GitHubAPIError` 回傳給模型
- **彈性**：未來可以在呼叫前後加入 rate limit、快取、日誌等邏輯

### System Prompt 設計

`_SYSTEM_PROMPT` 是這個專案中唯一的「prompt engineering」層，每個規則都對應一類 eval 失敗：

```
## Typo correction
在呼叫任何 tool 前，先靜默修正 repo name、org name、
程式語言名稱的明顯錯別字。
（修復依據：typo 類 eval 初始全部 fail，模型直接用錯誤拼字呼叫 API）

## search_repositories — q is always required
q 參數必填，永遠不能空呼叫。
模糊查詢時的 fallback 策略：
- 「最受歡迎」→ q="stars:>10000"
- 「有趣的開源專案」→ q="stars:>1000 pushed:>2024-01-01"
- 「最近很紅」→ q="created:>2024-01-01 stars:>1000"
（修復依據：fuzzy 類 eval 出現 tool call missing required argument 錯誤）

## Contradictory or impossible conditions
邏輯上不可能的條件，解釋原因而非嘗試搜尋。
（修復依據：模型面對矛盾條件會回傳空結果但不解釋，eval 視為 pass
 但品質不足）

## Language
永遠用使用者輸入的語言回覆。
（修復依據：multilingual eval 偶爾用英文回覆日文輸入）
```

---

## 現況與計畫

| Phase | 狀態 | 說明 |
|---|---|---|
| Phase 1 — 核心 CLI | ✅ 完成 | 互動對話、Function Calling、session 持久化 |
| Phase 2 — 強化層 | ✅ 完成 | Eval 框架、typo 容錯、模糊查詢 fallback、system prompt 強化 |
| Phase 3 — 多模型評測 | 未開始 | LiteLLM 跨模型評測 pipeline |

詳見 [`specs/roadmap.md`](specs/roadmap.md)。

---

## Eval 框架（Part 2 入口）

`evals/` 目錄包含系統性測試工具，用於驗證自然語言理解的邊緣案例：

```bash
# 執行完整 eval（需設定 GEMINI_API_KEY）
uv run python evals/run_evals.py

# 只跑特定類別
uv run python evals/run_evals.py --category typo
uv run python evals/run_evals.py --category fuzzy
```

`evals/queries.yaml` 包含 30 條測試案例，分為五類：

| 類別 | 數量 | 說明 |
|---|---|---|
| `fuzzy` | 6 | 模糊輸入，沒有明確 API 參數對應 |
| `typo` | 6 | 常見拼字錯誤（語言名稱、org/repo 名稱） |
| `contradiction` | 6 | 邏輯上不可能的條件 |
| `multilingual` | 6 | 日文、韓文輸入 |
| `multi_step` | 6 | 需要兩次以上 tool call 的查詢 |

結果存入 `evals/results.json`（append 模式，保留歷史）。每筆 result 包含完整回覆（`response_full`）、實際呼叫的工具列表（`tools_called`）、執行時間與 pass/fail/error 狀態。

---

## Phase 2 強化內容

### 問題發現流程

Phase 1 完成後，我設計了 30 條邊緣案例（`evals/queries.yaml`）並跑第一輪 eval，初始結果 23/30 pass，失敗集中在三類：

1. **工具呼叫錯誤（error）**：Gemini 嘗試呼叫 `search_repositories` 但沒有帶 `q` 參數 → SDK 拋出 validation error → 整筆 eval 記錄為 error
2. **404 / 301 錯誤**：`microsfot/vscode` 拼錯導致 404；`tiangolo/fastapi` 已遷移到 `fastapi/fastapi` 但 httpx 預設不追蹤 301
3. **回應語言錯誤**：日文輸入收到英文回覆

以下說明各問題的根因分析與修復決策：

### 已修復

**錯別字容錯（Typo Tolerance）**

在 system prompt 加入 typo correction 指引，要求 Gemini 在呼叫任何 API 前先修正明顯拼字錯誤（如 `pytohn→python`、`microsfot→microsoft`、`javascrpit→javascript`）。修復後 typo 類 6 條全部 pass。

**模糊查詢的 `q` 參數策略**

`search_repositories` 的 `q` 參數為必填，但面對「找個有趣的開源專案」這類完全模糊的查詢，Gemini 原先會嘗試不帶參數呼叫而導致 error。system prompt 現在明確規定：
- 「最受歡迎」類 → `q="stars:>10000"`
- 「有趣的開源專案」類 → `q="stars:>1000 pushed:>2025-01-01"`
- 「最近很紅」類 → `q="created:>2025-01-01 stars:>1000"`

**GitHub repo 重新導向（301 Redirect）**

GitHub 在 repo 遷移或重命名後會回傳 301。`github_api.py` 加入 `follow_redirects=True`，httpx 現在自動追蹤重新導向。

---

## 已知限制

以下為根本上難以完整解決的問題：

### 1. 模糊輸入的近似解

GitHub REST API 沒有官方 trending endpoint。ghibli 以 `created:>2025-01-01 sort:stars` 來近似「近期熱門」，eval 顯示能找出 OpenClaw、Hermes Agent 等 AI Agent repo，但這只是近似法——star 增長快速但創建時間較早的 repo 可能被遺漏。

### 2. 矛盾條件依賴 Gemini 推理

「找 star 超過 100 萬的 repo」、「列出同時 open 又 closed 的 PR」等邏輯矛盾查詢，GitHub API 本身不驗證可能性，只回傳空結果。Gemini 在 eval 中能正確識別 6 條矛盾條件並給出解釋，但這依賴模型推理，非程式層保證。

### 3. 錯別字修正的邊界

typo correction 依賴 Gemini 推理，沒有規則式驗證。語意歧義的情況（如「linus」可能是人名也可能是 repo 名 `linux`）仍可能修正錯誤方向。

### 4. 非繁中多語言

日文、韓文在 eval 6 條查詢均 pass，但屬未正式驗證的行為。複雜多步驟的日韓文查詢準確性不保證。
