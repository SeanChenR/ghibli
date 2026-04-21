## 1. 專案結構與設定（pyproject.toml）

- [x] 1.1 [P] 更新 `pyproject.toml`：填入 PEP 621 metadata（name="ghibli", version="0.1.0", requires-python=">=3.12"），加入 runtime 依賴：`typer>=0.12`、`google-genai>=1.0`、`rich>=13`、`httpx>=0.27`、`python-dotenv>=1`（對應：package metadata and dependencies declared in pyproject.toml）
- [x] 1.2 [P] 更新 `pyproject.toml`：在 `[project.scripts]` 加入 `ghibli = "ghibli.cli:app"`（對應：CLI entry point registered as a script）
- [x] 1.3 [P] 更新 `pyproject.toml`：在 `[project.optional-dependencies]` 下的 `dev` 群組加入 `pytest>=8`、`pytest-cov>=5`、`ruff>=0.4`、`black>=24`；設定 `[tool.pytest.ini_options]`（testpaths=["tests"]、addopts="--cov=src/ghibli --cov-report=term-missing --cov-fail-under=80"）；設定 `[tool.ruff]`（line-length=88、select=["E","F","I"]）；設定 `[tool.black]`（line-length=88）（對應：test tooling configured in pyproject.toml）
- [x] 1.4 [P] 更新 `pyproject.toml`：加入 `[tool.setuptools.packages.find]`，設定 `where = ["src"]`，確保套件從 src/ 目錄尋找（對應：source layout follows src/ convention）
- [x] 1.5 [P] 建立 `src/ghibli/` 套件骨架：`__init__.py`（含 `__version__ = "0.1.0"`）、`cli.py`（空 Typer app 骨架，只含 `app = typer.Typer()`）、`tools.py`（空模組）、`github_api.py`（空模組）、`sessions.py`（空模組）、`output.py`（空模組）（對應：source layout follows src/ convention）
- [x] 1.6 [P] 建立測試目錄結構：`tests/__init__.py`、`tests/unit/__init__.py`、`tests/integration/__init__.py`、`tests/conftest.py`（含空的 `# shared fixtures will go here` 注解）（對應：test directory structure established）
- [x] 1.7 [P] 新增 `.env.example`：以 `# --- Gemini 認證（二擇一）---` 為分組標題；列出 `GEMINI_API_KEY=your_gemini_api_key_here`（標記 `# Option 1: API Key 模式`，附說明）；列出 `VERTEX_PROJECT=your_gcp_project_id`（標記 `# Option 2: Vertex AI 模式`，說明需搭配 ADC）；列出 `VERTEX_LOCATION=us-central1`（標記 `# Vertex AI 模式選用，預設 us-central1`）；另加 `GITHUB_TOKEN=your_github_pat_here`（標記 `# 選用，提高 GitHub API rate limit 至 5000 req/hr`）（對應：environment variable template provided）

## 2. 例外類別（TDD — 先寫測試，再實作）

- [x] 2.1 [P] 在 `tests/unit/test_exceptions.py` 寫失敗測試（Red）：`test_ghibli_error_is_exception()` 驗證 `issubclass(GhibliError, Exception)` 為 True；`test_any_subclass_catchable_as_ghibli_error()` raise `ToolCallError("x")` 並確認 `except GhibliError` 可捕捉（對應：base exception class GhibliError defined）
- [x] 2.2 [P] 在 `tests/unit/test_exceptions.py` 寫失敗測試（Red）：`test_tool_call_error_carries_message()` 驗證 `str(ToolCallError("msg"))` 含 `"msg"`；`test_tool_call_error_is_ghibli_error()` 驗證 isinstance 關係（對應：ToolCallError raised for LLM tool-calling failures）
- [x] 2.3 [P] 在 `tests/unit/test_exceptions.py` 寫失敗測試（Red）：`test_github_api_error_exposes_status_code()` 驗證 `GitHubAPIError("not found", status_code=404).status_code == 404`；`test_github_api_error_is_ghibli_error()` 驗證 isinstance 關係（對應：GitHubAPIError raised for GitHub REST API failures）
- [x] 2.4 [P] 在 `tests/unit/test_exceptions.py` 寫失敗測試（Red）：`test_session_error_is_ghibli_error()` 驗證 `isinstance(SessionError("db error"), GhibliError)` 為 True；`test_output_error_is_ghibli_error()` 驗證 `isinstance(OutputError("render failed"), GhibliError)` 為 True（對應：SessionError raised for session storage failures、OutputError raised for output formatting failures）
- [x] 2.5 在 `src/ghibli/exceptions.py` 實作（Green）：`GhibliError(Exception)`；`ToolCallError(GhibliError)`；`GitHubAPIError(GhibliError)` 接受 `message: str` 與 `status_code: int` 關鍵字參數；`SessionError(GhibliError)`；`OutputError(GhibliError)` — 執行 `pytest tests/unit/test_exceptions.py` 直到全部通過（對應：GhibliError, ToolCallError, GitHubAPIError, SessionError, OutputError）

## 3. 驗證

- [x] 3.1 執行 `uv sync --dev` 確認所有依賴安裝成功且無衝突；執行 `uv pip install -e .` 確認 `ghibli --help` 可運作（對應：CLI entry point registered as a script）
- [x] 3.2 執行 `pytest tests/unit/` 確認所有例外類別測試通過；執行 `ruff check src/` 確認無 lint 錯誤（對應：test tooling configured in pyproject.toml）
