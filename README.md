# ghibli — GitHub Intelligence Bridge

用自然語言查詢 GitHub，不需要記住 API 格式。

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

## 現況與計畫

| Phase | 狀態 | 說明 |
|---|---|---|
| Phase 1 — 核心 CLI | ✅ 完成 | 互動對話、Function Calling、session 持久化 |
| Phase 2 — 強化層 | 未開始 | 輸入清洗、typo 容錯、模糊查詢 fallback |
| Phase 3 — 多模型評測 | 未開始 | LiteLLM 跨模型評測 pipeline |

詳見 [`specs/roadmap.md`](specs/roadmap.md)。
