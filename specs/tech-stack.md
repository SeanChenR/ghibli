# Tech Stack — ghibli

## 語言與環境

| 項目 | 選型 | 原因 |
|---|---|---|
| 語言 | Python 3.12 | 生態系成熟，LLM SDK 支援完整 |
| 套件管理 | uv | 速度快、lockfile 支援、現代 Python 工具鏈 |

---

## CLI 框架

**選型：Typer**

基於 Click，型別提示自動生成 CLI 介面。對話模式啟動後進入互動式 loop；也支援 `--session` 參數載入歷史 session。

```
ghibli                        # 開新 session，進入對話
ghibli --session <id>         # 載入既有 session 繼續對話
ghibli --list-sessions        # 列出過去的 sessions
```

---

## LLM 整合

### Phase 1 — Google Generative AI Python SDK（`google-genai`）

使用 Gemini 2.5 Flash 的 **Function Calling** 功能，將 6 個 GitHub API 操作定義為 tools，讓 Gemini 自行決定何時呼叫、呼叫幾次：

```python
# tools 透過 GenerateContentConfig 傳入（SDK >= 1.0 必要）
# automatic_function_calling 停用，保留手動 loop 控制
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=conversation_history,
    config=types.GenerateContentConfig(
        tools=_TOOLS,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    ),
)
```

支援兩種認證方式（優先順序：API Key > Vertex AI）：
- **API Key 模式**：`GEMINI_API_KEY` 環境變數
- **Vertex AI 模式**：`GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` + Google ADC

### Phase 3 — LiteLLM

統一介面跨模型評測（Gemini、GPT-4o、Llama 3 via Ollama），測試同一組 tool definitions 在不同模型上的表現。

---

## Session 儲存

**選型：SQLite（`~/.ghibli/sessions.db`）**

原因：Phase 3 eval 需要跨 session 查詢（`SELECT` tool calls by model），SQLite 比 JSONL 更適合結構化查詢。Python 內建 `sqlite3`，零額外依賴。

Schema 概念：
```sql
sessions(id, created_at, updated_at, title)
turns(id, session_id, role, content_json,
      tool_name, tool_args_json, tool_result_json, created_at)
```

儲存路徑：`~/.ghibli/sessions.db`（跨 session 持久化）

---

## 目標 API

**GitHub REST API（公開端點）**

- 認證：GitHub Personal Access Token（`GITHUB_TOKEN` 環境變數，選用）
- 速率限制：已認證 5000 req/hr，未認證 60 req/hr
- Phase 1 支援的 tools：`search_repositories`、`get_repository`、`list_issues`、`list_pull_requests`、`get_user`、`list_releases`

---

## 輸出格式

| 模式 | 實作 | 觸發方式 |
|---|---|---|
| 預設（自然語言 + 表格） | Rich | 直接對話 |
| 原始 tool 結果 JSON | `json` 模組 | 加 `--json` flag |

---

## 測試與品質

| 工具 | 用途 |
|---|---|
| pytest + pytest-cov | 單元測試，覆蓋率門檻 80% |
| ruff | Linting + import 排序 |
| black | 程式碼格式化 |

覆蓋率門檻在 `pyproject.toml` 以 `--cov-fail-under=80` 強制執行。

---

## 專案結構（當前）

```
ghibli/
├── specs/                  # 專案層級規格（本資料夾）
├── openspec/               # Feature-level spec（Spectra SDD）
├── src/
│   └── ghibli/
│       ├── __init__.py
│       ├── cli.py          # Typer CLI + conversation loop
│       ├── agent.py        # Gemini Function Calling loop + session 歷史管理
│       ├── tools.py        # GitHub tool definitions（6 個 Python callable）
│       ├── github_api.py   # GitHub REST API HTTP 執行層
│       ├── sessions.py     # SQLite session 讀寫
│       ├── output.py       # Rich Markdown / JSON 輸出
│       └── exceptions.py   # GhibliError 階層
├── tests/
│   └── unit/               # 50 個單元測試，87% 覆蓋率
├── pyproject.toml
└── README.md
```

---

## 環境變數

```bash
# Gemini 認證（二擇一）
GEMINI_API_KEY=...              # Option 1: API Key 模式
GOOGLE_CLOUD_PROJECT=...        # Option 2: Vertex AI 模式
GOOGLE_CLOUD_LOCATION=us-central1  # Vertex AI 選用，預設 us-central1

# GitHub API 認證（選用）
GITHUB_TOKEN=...                # 提高 rate limit 至 5000 req/hr

# Phase 3 Multi-model eval（待實作）
OPENAI_API_KEY=...              # GPT-4o 評測用
```
