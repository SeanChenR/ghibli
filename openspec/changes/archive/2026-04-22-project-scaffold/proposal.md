## Why

ghibli 目前只有空的 `main.py` 和 `pyproject.toml`，缺乏正式的套件結構、依賴宣告、測試基礎設施與開發工具設定。在開始任何功能開發之前，必須先建立可運作的專案骨架，確保所有後續 change 都在一致的環境上進行。

## What Changes

- 將 `pyproject.toml` 補上所有 Phase 1 依賴（Typer、google-genai、Rich、httpx）與開發依賴（pytest、pytest-cov、ruff、black、python-dotenv）
- 建立 `src/ghibli/` 套件目錄，包含 `__init__.py`、空的模組骨架（`cli.py`、`tools.py`、`github_api.py`、`sessions.py`、`output.py`）
- 建立 `src/ghibli/exceptions.py`，定義 `GhibliError` 基礎例外類別與子類別
- 建立 `tests/` 目錄結構（`unit/`、`integration/`、`conftest.py`）
- 新增 `.env.example` 說明所需環境變數（Gemini API Key 或 Vertex AI 二擇一）
- 設定 `pyproject.toml` 中的 `[tool.pytest]`、`[tool.ruff]`、`[tool.black]` 配置區塊
- 設定 `pyproject.toml` 中的 `[project.scripts]` entry point：`ghibli = "ghibli.cli:app"`

## Non-Goals

- 不實作任何功能邏輯（CLI 指令、LLM 呼叫、GitHub API 請求）
- 不設定 CI/CD pipeline
- 不處理 Phase 2 或 Phase 3 的依賴（LiteLLM、Ollama）

## Capabilities

### New Capabilities

- `project-configuration`: 專案依賴宣告、開發工具設定、套件 entry point、目錄結構規範
- `exception-hierarchy`: `GhibliError` 基礎例外類別與子類別（`ToolCallError`、`GitHubAPIError`、`SessionError`、`OutputError`）

### Modified Capabilities

（無）

## Impact

- 新增/修改的檔案：
  - `pyproject.toml`（全面更新）
  - `src/ghibli/__init__.py`
  - `src/ghibli/cli.py`（空骨架）
  - `src/ghibli/tools.py`（空骨架）
  - `src/ghibli/github_api.py`（空骨架）
  - `src/ghibli/sessions.py`（空骨架）
  - `src/ghibli/output.py`（空骨架）
  - `src/ghibli/exceptions.py`
  - `tests/__init__.py`
  - `tests/unit/__init__.py`
  - `tests/integration/__init__.py`
  - `tests/conftest.py`
  - `.env.example`
- 依賴：無外部依賴（此 change 本身就是在建立依賴清單）
