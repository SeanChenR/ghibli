## Why

ghibli 的首次使用者體驗原本依賴使用者自己讀 `--help` 加 README 組合 `--model openai:gpt-4o-mini` 這種 flag；進對話沒有 context、慢模型完全靜默、退出也不知道 session 有沒有保存。Typer 預設注入的 `--install-completion` / `--show-completion` 污染 `--help`。這個 change 把首次體驗從「read the docs」升級到「啟動即可用」，並讓 agent 呼叫 tool 的推理過程可視化。

**2026-04-23 redesign（post-dogfood）**：原本「靠環境變數偵測已配置 provider」的 picker 在實際使用時發現兩個問題——(a) 上層目錄 `.env`（例如 `~/.env`）或 shell 自動 export 會污染偵測結果，使用者以為專案 `.env` 刪了就乾淨但 picker 仍看到 key；(b) 真實使用者期望「上次選什麼、這次沿用」而不是每次都重新偵測。因此改為**顯式選擇 + 持久化**：picker 一律列 5 個選項（不看 env）、使用者選完寫入 `.ghibli/last_model`、下次直接用；加 `--model-picker` flag 給「想換 model」的場景；SQLite session DB 一併搬到 project-local `.ghibli/sessions.db`，讓一個 repo 一套狀態、跨 repo 不互相污染。

## What Changes

- **模型解析採固定優先順序，無隱式預設**：`--model <id>` → `GHIBLI_MODEL` env → `.ghibli/last_model` → picker。所有都落空才跳 picker；沒有「找不到就 fallback 到 gemini-2.5-flash」這種 silent 行為。
- **Picker 固定列 5 個選項**（不再依環境變數篩選）：Gemini 2.5 Flash (API Key) / Gemini 2.5 Flash (Vertex AI) / Gemma-4-26b / OpenAI gpt-4o-mini / Ollama Cloud。使用者選完將結果寫入 `.ghibli/last_model`。
- **`--model-picker` flag**：即使已有 `last_model`，也強制顯示 picker；選完更新記憶。
- **Onboarding 擴充涵蓋 Vertex AI**：選了缺 credential 的 provider 時進 setup——API Key 類沿用 `typer.prompt(hide_input=True)` 取得 key 後 append 到 `.env`；Vertex AI 類提示使用者跑 `gcloud auth application-default login`（ADC），再 prompt 輸入 `GOOGLE_CLOUD_PROJECT`（與選用的 `GOOGLE_CLOUD_LOCATION`）寫入 `.env`。
- **SQLite session DB 搬到 project-local**：從 `~/.ghibli/sessions.db` 改到 `<cwd>/.ghibli/sessions.db`（與 `last_model` 共處同目錄）；配合 `.gitignore` 加 `.ghibli/` 讓它不被 commit。每個 repo 有獨立 session，跨平台（Mac / Linux / Windows）不依賴 home directory 結構。
- **`.env` 讀取只看專案本身**：`load_dotenv(dotenv_path=Path.cwd() / ".env")` 明確指定，避免 python-dotenv 預設 `find_dotenv` 往上搜尋讀到 `~/.env` 這種污染。
- **新增 Gemma-4 via LiteLLM 路由**：`agent.py` 加 `gemini:<slug>` prefix，對稱於現有的 `openai:` / `ollama:`；picker 選 Gemma 時送 `gemini:gemma-4-26b-a4b-it`。
- **Tool call 可視化**：`agent.chat()` 新增 `on_tool_call: Callable[[str, dict], None] | None = None`；CLI 傳入以 `→ search_repositories(q="...")` 格式即時印出 agent 呼叫的每個 tool。
- **Rich 外觀**：啟動 welcome banner 顯示 model + session id + 簡短 hint；等模型回覆時 `⠋ Thinking...` spinner；退出印 resume 指令。
- **Session 生命週期**：退出時若 session 的 turns 數為 0 自動刪除；turns > 0 則印 `Session saved: <id> (N turns)\nResume with: ghibli --session <id>`。
- **`--session <id>` 恢復行為**：沿用 `.ghibli/last_model`（或 `--model` 覆寫），不再強制跳 picker——使用者可以直接接續之前的對話。
- **`--help` 清理**：`typer.Typer(add_completion=False)` 移除 `--install-completion` / `--show-completion`。

## Non-Goals

- 不持久化「某個 session 當時用了哪個 model」（只記**最後一次**的全域選擇）。Session 歷史載入後可由任何 model 處理，這是刻意的簡化。
- 不做 API key 的線上 validation（onboarding 期間不打測試 request）；錯的 key 在第一輪 chat 會清楚報錯。
- 不引入 `questionary` / `InquirerPy` 等互動 UI 依賴（用 typer 內建 + Rich 已有 renderer）。
- 不改動 eval pipeline（`evals/run_evals.py`、`evals/models.py`）。
- 不在 shell / home 層級讀 `.env`（這次 redesign 的核心取捨之一）。

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `cli-interface`: picker、`--model-picker` flag、onboarding（API Key + Vertex）、tool 可視化、Rich 外觀、退出提示、`--help` 清理、model 解析優先順序、`.ghibli/last_model` 持久化
- `session-storage`: SQLite DB 從 home 搬至 `<cwd>/.ghibli/sessions.db`、`last_model` 檔案 CRUD、空 session 自動刪除、`count_turns` / `delete_session`
- `gemini-authentication`: `.env` 只讀 cwd（不往上找）、Vertex AI onboarding（ADC + project id）、API Key onboarding（append 到 `.env`、不覆蓋既有 key）
- `gemini-function-calling`: `on_tool_call` callback、`gemini:<slug>` LiteLLM 路由

## Impact

- Affected specs:
  - Modified: `cli-interface`, `session-storage`, `gemini-authentication`, `gemini-function-calling`
- Affected code:
  - Modified: `src/ghibli/cli.py`（picker 流程、model 解析順序、`--model-picker` flag、welcome banner、spinner、tool viz、退出邏輯、`--help` 清理、`load_dotenv` 明確路徑）
  - Modified: `src/ghibli/agent.py`（`on_tool_call` callback、`gemini:` 路由、移除 `gemini-2.5-flash` default fallback）
  - Modified: `src/ghibli/sessions.py`（DB_PATH 改 `<cwd>/.ghibli/sessions.db`、auto-create dir、`count_turns`、`delete_session`）
  - Modified: `src/ghibli/picker.py`（5 選項固定、`read_last_model` / `write_last_model`、Vertex onboarding、移除環境變數偵測）
  - Modified: `tests/unit/test_cli.py`、`tests/unit/test_agent.py`、`tests/unit/test_sessions.py`、`tests/unit/test_picker.py`
  - Modified: `README.md`（picker 流程 / `.ghibli/` 介紹 / onboarding 情境 / `--model-picker`）
  - Modified: `CLAUDE.md`（新增關鍵架構決策：model 解析順序、project-local `.ghibli/`、last_model 持久化）
  - Modified: `.env.example`
  - Modified: `.gitignore`（加 `.ghibli/`）
- Affected dependencies: 不新增任何 runtime 依賴
