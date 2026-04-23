## 1. Gemini LiteLLM 路徑（Gemma-4 走 LiteLLM，`agent.py` 加 `gemini:<slug>` 前綴）

- [x] 1.1 在 `tests/unit/test_agent.py` 加測試涵蓋 gemini: prefix routes chat to LiteLLM with Gemini provider：`gemini:gemma-4-26b-a4b-it` 走 LiteLLM（檢查 `model="gemini/gemma-4-26b-a4b-it"` 與 `api_key`）、bare `gemini-2.5-flash` 仍用 native SDK（檢查 `genai.Client` 被呼叫而 `litellm.completion` 沒有）、缺 `GEMINI_API_KEY` 時 `gemini:` 前綴應拋 `ToolCallError`
- [x] 1.2 在 `src/ghibli/agent.py` 的 `chat()` 加 `gemini:` prefix 路由分支，走 `_chat_litellm(model_id=f"gemini/{slug}", api_key=os.environ["GEMINI_API_KEY"], provider_label="Gemini")`；確保 1.1 的測試全綠

## 2. Tool call callback（Tool call 可視化用 callback，不動 chat 回傳型別）

- [x] 2.1 在 `tests/unit/test_agent.py` 加測試涵蓋 on_tool_call callback invoked per tool dispatch：Gemini 路徑 + LiteLLM 路徑各驗證「每次 dispatch 呼叫 callback 一次、參數正確、順序正確」、default `None` 行為不變、callback 內拋 `RuntimeError` 時 chat 不中斷且最終文字仍正確返回
- [x] 2.2 在 `src/ghibli/agent.py` `chat()` 加 keyword-only 參數 `on_tool_call: Callable[[str, dict], None] | None = None`；在 Gemini 與 LiteLLM 兩條路徑的 tool dispatch 之前以 `try/except Exception` 包住呼叫 callback，例外寫入 stderr 但不重拋

## 3. Sessions CRUD 擴充（空 session 清除在退出時做）

- [x] 3.1 在 `tests/unit/test_sessions.py` 加測試涵蓋 count_turns returns the number of turns for a session：new session 回 0、append 兩個 turn 後回 2、unknown id 回 0 不拋例外
- [x] 3.2 在 `src/ghibli/sessions.py` 實作 `count_turns(session_id: str) -> int`：`SELECT COUNT(*) FROM turns WHERE session_id = ?`
- [x] 3.3 在 `tests/unit/test_sessions.py` 加測試涵蓋 delete_session removes a session row and all its turns：empty session 刪後 `get_session` 回 None、有 3 個 turns 的 session 刪後 `get_turns` 回 `[]` 且 `get_session` 回 None、unknown id 刪除不拋例外
- [x] 3.4 在 `src/ghibli/sessions.py` 實作 `delete_session(session_id: str) -> None`：先刪 `turns` 再刪 `sessions`，`sqlite3.Error` 包成 `SessionError`

## 4. Picker 模組 v1（已完成，部分內容將在 10/11 被 redesign 覆寫）

- [x] 4.1 建立 `tests/unit/test_picker.py`，加測試涵蓋 append_env_var persists a new API key to .env without overwriting：`.env` 不存在時建立並寫一行、存在無該 key 時 append（前置 `\n` 若需要）、存在有該 key 時不動檔案並拋例外訊息包含 key 名稱
- [x] 4.2 在 `src/ghibli/picker.py` 實作 `append_env_var(key: str, value: str, env_path: Path | None = None) -> None`：UTF-8、明確 `"\n"` line terminator、行首匹配 `^<key>=` 偵測既有 key
- [x] 4.3 在 `tests/unit/test_picker.py` 加測試涵蓋 Interactive model picker on launch（v1 版本：環境變數偵測；section 10 會改寫為固定 5 選項）
- [x] 4.4 在 `src/ghibli/picker.py` 實作 `choose_model() -> str | None`（v1 版本：偵測 env；section 10 會改寫為固定 5 選項 + 寫入 last_model）
- [x] 4.5 在 `tests/unit/test_picker.py` 加測試涵蓋 Zero-provider onboarding writes key to .env 與 Onboarding flow uses append_env_var to persist setup keys（v1：只含 API Key 分支；section 11 擴充 Vertex）
- [x] 4.6 在 `src/ghibli/picker.py` 實作 `run_onboarding() -> str`（v1：只含 API Key；section 11 加 Vertex 分支）

## 5. CLI 整合 v1（已完成，picker 觸發條件將在 8/12 被 redesign 覆寫）

- [x] 5.1 在 `tests/unit/test_cli.py` 加測試涵蓋 --help excludes Typer completion commands：`runner.invoke(app, ["--help"])` 的輸出不含 `--install-completion` 與 `--show-completion`
- [x] 5.2 在 `src/ghibli/cli.py` 把 `typer.Typer(invoke_without_command=True)` 改為 `typer.Typer(invoke_without_command=True, add_completion=False)`
- [x] 5.3 在 `tests/unit/test_cli.py` 加測試涵蓋 --model flag selects model and bypasses picker（v1：TTY + 無 --model 觸發；section 8 改為加上 last_model 優先順序）
- [x] 5.4 在 `src/ghibli/cli.py` 的 `main()` 加 picker 接入邏輯（v1：TTY gate；section 8 改為多來源解析）
- [x] 5.5 在 `tests/unit/test_cli.py` 加測試涵蓋 Welcome banner on start、Thinking spinner during agent work、Tool call visualization during agent work：welcome banner 呼叫一次、spinner 在 `agent.chat` 期間啟用、`on_tool_call` callback 傳入 agent 並觸發時印 `→ tool_name(...)` 格式
- [x] 5.6 在 `src/ghibli/cli.py` 加 welcome banner（Rich 風格，含 model、session id、簡短 hint，每次啟動印一次）、`agent.chat` 呼叫前後用 Rich `Status` / `Progress` 顯示 `Thinking...` spinner、將 `on_tool_call` callback 以 lambda 傳給 `agent.chat` 以 `→ {name}({args_preview})` 格式印到 Rich console
- [x] 5.7 在 `tests/unit/test_cli.py` 加測試涵蓋 Session save hint on exit：有 ≥1 turn 的 session 退出時印 `Session saved: <id>` 與 `Resume with: ghibli --session <id>`；0 turn 的 session 退出時呼叫 `sessions.delete_session`、不印 resume hint
- [x] 5.8 在 `src/ghibli/cli.py` 的退出邏輯（空行 / Ctrl+C / Ctrl+D）加：呼叫 `sessions.count_turns(session_id)`，若 `> 0` 印 save + resume 訊息，若 `== 0` 呼叫 `sessions.delete_session(session_id)` 僅印 farewell

## 6. 文件與環境範本 v1（已完成，redesign 後會再 section 14 更新）

- [x] 6.1 [P] 更新 `README.md` 的「支援的模型與快速配置」章節：描述 picker 互動流程、onboarding 寫 `.env` 行為、`--model` 仍為 bypass 入口
- [x] 6.2 [P] 更新 `.env.example`：加註解說明首次啟動無 key 時會 onboarding 自動 append 到 `.env`
- [x] 6.3 [P] 更新 `CLAUDE.md`：於「關鍵架構決策」加入 picker 與 `gemini:` prefix 的說明

## 7. 手動驗證（redesign 後重新定義；舊版 v1 smoke tests 被 section 13 取代）

- [x] 7.8 執行 `uv run pytest` 與 `uv run ruff check src/`，確認全部測試綠且覆蓋率 ≥ 80%（已在 v1 跑完；redesign landing 後需再跑一次）

## 8. Last-model 持久化 + 無預設 model 解析

- [x] 8.1 在 `tests/unit/test_picker.py` 加測試涵蓋 last_model file read and write：`read_last_model()` 檔案不存在時回 `None`；`write_last_model("openai:gpt-4o-mini")` 後再 `read_last_model()` 回相同字串（不含尾端 `\n`）；`write_last_model` 自動建立 `<cwd>/.ghibli/` 目錄
- [x] 8.2 在 `src/ghibli/picker.py` 實作 `read_last_model() -> str | None` 與 `write_last_model(identifier: str) -> None`：讀取檔案 strip whitespace；寫入時自動 `mkdir(parents=True, exist_ok=True)`、用 `"{id}\n"` 格式 UTF-8
- [x] 8.3 在 `tests/unit/test_cli.py` 加測試涵蓋 Model resolution priority (no silent default)：驗證優先順序 `--model > GHIBLI_MODEL > .ghibli/last_model > picker`；驗證 `--model` 傳入時不更動 `last_model`；驗證全部來源缺且 stdin 非 TTY 時 CLI 以 code 1 結束並在 stderr 印 `--model`
- [x] 8.4 在 `src/ghibli/cli.py` 的 `main()` 改寫 model 解析邏輯為優先順序四層（flag → env → last_model → picker），picker 選完後呼叫 `picker.write_last_model()` 持久化；非 TTY 無來源時 `typer.Exit(code=1)` 並印錯誤訊息
- [x] 8.5 在 `src/ghibli/agent.py` 移除 `chat()` 內 `ghibli_model = model or os.environ.get("GHIBLI_MODEL", "gemini-2.5-flash")` 的 `"gemini-2.5-flash"` silent default fallback；改為若 `ghibli_model` 為 None 則拋 `ToolCallError`（表示呼叫方責任）

## 9. SQLite 搬家到 project-local `.ghibli/sessions.db`

- [x] 9.1 在 `tests/unit/test_sessions.py` 加測試涵蓋 SQLite database initialized at project-local `.ghibli/sessions.db`：當 `<cwd>/.ghibli/sessions.db` 不存在時呼叫任一 session 函式會自動建立 `.ghibli/` 與 DB；舊 home 路徑 `~/.ghibli/sessions.db` 不被觸及
- [x] 9.2 在 `src/ghibli/sessions.py` 把 `DB_PATH` 從 `Path.home() / ".ghibli" / "sessions.db"` 改成 `Path.cwd() / ".ghibli" / "sessions.db"`；`_get_connection()` 的 `parent.mkdir(parents=True, exist_ok=True)` 自動建 `.ghibli/`
- [x] 9.3 在 `.gitignore` 加入 `.ghibli/` 一行，避免 SQLite DB、last_model、其他 project-local state 被誤 commit

## 10. Picker 改為固定 5 選項（移除 env 偵測）

- [x] 10.1 在 `tests/unit/test_picker.py` 改寫 picker 測試涵蓋 Interactive model picker on launch 的新行為：`choose_model()` 一律列 5 個選項（Gemini API Key / Gemini Vertex AI / Gemma-4 / OpenAI / Ollama Cloud），不依環境變數過濾；選擇後回傳對應 model identifier 並呼叫 `write_last_model`
- [x] 10.2 在 `src/ghibli/picker.py` 改寫 `_PROVIDERS` 為 5 項固定列表（加入 Vertex AI 獨立選項）；移除 `_is_configured` 與 env_any 邏輯；`choose_model` 一律 prompt（除非 stdin 非 TTY）；選擇後 `write_last_model()`
- [x] 10.3 在 `tests/unit/test_picker.py` 加測試涵蓋 Selection is persisted to last_model：picker 選完後 `<cwd>/.ghibli/last_model` 內容為所選 identifier + `\n`

## 11. Vertex AI onboarding

- [x] 11.1 在 `tests/unit/test_picker.py` 加測試涵蓋 Vertex AI onboarding guides user through ADC setup：使用者選 Vertex AI 時 stdout 含 `gcloud auth application-default login` 字串；prompt 輸入 `GOOGLE_CLOUD_PROJECT` → `append_env_var("GOOGLE_CLOUD_PROJECT", ...)` 被呼叫；`GOOGLE_CLOUD_LOCATION` 接受 default `us-central1` 時不寫入
- [x] 11.2 在 `src/ghibli/picker.py` 的 `run_onboarding` 加 Vertex AI 分支：印 ADC 指引 → 等待 Enter → prompt project id → prompt location（default `us-central1`）→ 呼叫 `append_env_var` 寫入；回傳 `gemini-2.5-flash` 作為 model identifier

## 12. `--model-picker` flag

- [x] 12.1 在 `tests/unit/test_cli.py` 加測試涵蓋 --model-picker flag forces re-selection and updates last_model：即使 `.ghibli/last_model` 已有值，加 `--model-picker` 會觸發 picker；選完新值後 `last_model` 被覆寫
- [x] 12.2 在 `src/ghibli/cli.py` 加 `--model-picker` 布林 option（Typer）；`main()` 偵測到該 flag 時跳過 flag/env/last_model 解析，強制進 `picker.choose_model()`

## 13. `.env` 讀取只限專案 cwd

- [x] 13.1 在 `tests/unit/test_cli.py` 加測試涵蓋 Project-local .env read only：驗證 `cli.py` 呼叫 `load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)`；當 `~/.env` 有值但 cwd 沒 `.env` 時，`os.environ` 相關 key 不被注入
- [x] 13.2 確認 `src/ghibli/cli.py` 的 `load_dotenv(...)` 呼叫使用明確 `dotenv_path=Path.cwd() / ".env"`（dogfood fix 期間已修，本 task 只是驗證 + 補測試）

## 14. Redesign 後的文件更新

- [x] 14.1 [P] 更新 `README.md`：描述新的 model 解析優先順序（`--model` → env → last_model → picker）、`.ghibli/` 目錄（`sessions.db` + `last_model`）、`--model-picker` 使用方式、Vertex AI onboarding 步驟
- [x] 14.2 [P] 更新 `CLAUDE.md` 的關鍵架構決策：新增「model 解析優先順序」「project-local `.ghibli/` 目錄」「last_model 持久化檔案」三個條目，修改原本的 picker 說明
- [x] 14.3 [P] 更新 `.env.example`：標註 Vertex AI 路徑走 `GOOGLE_CLOUD_PROJECT` + ADC，說明 `.env` 只從專案 cwd 讀；移除 `GHIBLI_MODEL` 提到 silent default 的註解

## 15. Smoke tests（redesign 後重新定義）

- [x] 15.1 Smoke test：刪 `.env` 與 `.ghibli/last_model` → 跑 `ghibli` → picker 出現 5 選項 → 選 OpenAI → onboarding 寫入 key → 進入對話 → `.ghibli/last_model` 含 `openai:gpt-4o-mini`
- [x] 15.2 Smoke test：有 `.ghibli/last_model=openai:gpt-4o-mini` → 跑 `ghibli` → 不顯示 picker、直接用 OpenAI
- [x] 15.3 Smoke test：`ghibli --model-picker` → 即使 `last_model` 存在仍顯示 picker → 選 Gemma → `last_model` 被覆寫為 `gemini:gemma-4-26b-a4b-it`
- [x] 15.4 Smoke test：`ghibli --model openai:gpt-4o` → picker 跳過、`last_model` 不變
- [x] 15.5 Smoke test：`echo "query" | ghibli`（無 `--model`、無 `GHIBLI_MODEL`、無 `last_model`）→ 以 code 1 結束並在 stderr 印 `--model`
- [x] 15.6 Smoke test：picker 選 Vertex AI + `GOOGLE_CLOUD_PROJECT` 未設 → 印出 `gcloud auth application-default login` 指引 → 輸入 project id → `.env` 含 `GOOGLE_CLOUD_PROJECT=<input>` → 進入對話
- [x] 15.7 Smoke test：`~/.env` 含 `GOOGLE_CLOUD_PROJECT=x` 但 `<cwd>/.env` 不含 → 跑 `ghibli`（無 `--model` 無 `last_model`）→ picker 顯示、不會誤把 Vertex 當已配置
- [x] 15.8 Smoke test：新 repo 第一次跑 `ghibli` → `<cwd>/.ghibli/` 目錄自動建立、含 `sessions.db` 與 `last_model`；`~/.ghibli/` 不被觸及
- [x] 15.9 跑 `uv run pytest` 全綠、覆蓋率 ≥ 80%（landing 完 section 8-14 的新程式碼後）
