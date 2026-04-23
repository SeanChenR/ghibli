## Context

ghibli CLI 原本啟動後直接進入 `You> ` 對話 loop；使用者必須先讀 README 或 `--help` 才知道有哪些 model 可選、怎麼切換。`--help` 本身又被 Typer 預設的 `--install-completion` / `--show-completion` 污染。對話過程中 `agent.chat()` 是一個黑盒——送出 query 後 CLI 靜默等待，慢模型（Ollama 的 qwen3.5:cloud 單條 60–90 秒）會讓使用者以為當機。退出時只印 `Bye!`，使用者不知道 session 被保存了，也沒有資訊可以接續。`agent.py` 目前支援 `openai:` 和 `ollama:` 兩個 LiteLLM prefix，但 Gemma-4 只存在於 `evals/models.py`（走 `gemini/gemma-4-26b-a4b-it`），CLI 不可用。

**2026-04-23 redesign context**：第一次實作後 dogfood 發現——(a) `load_dotenv()` 預設 `find_dotenv()` 會往 home 層找 `.env`，`~/.env` 裡的 `GOOGLE_CLOUD_PROJECT` 讓 picker 把 Gemini 2.5 Flash 視為已配置，使用者以為專案 `.env` 清了就乾淨但根本沒；(b) 使用者期望「上次選什麼這次繼續用」而非每次偵測；(c) Vertex AI 被當作隱式 fallback（`GOOGLE_CLOUD_PROJECT` 存在就走）比顯式選項容易誤觸。因此本 change 轉向「顯式選 + 持久化 + 專案本地化狀態」的模型，徹底移除環境變數偵測 + silent default。

這個 change 的最終目標：在不破壞 eval / CI / script 使用路徑的前提下，讓首次啟動體驗不用讀文件，同時讓 agent 推理過程對使用者透明，且狀態（session、last model）都放在專案目錄內、一個 repo 一套、易於在不同平台維運。

## Goals / Non-Goals

### Goals

- 首次啟動不需讀 README 就能選對 model 並開始對話
- Model 解析順序明確、沒有 silent fallback：`--model` > `GHIBLI_MODEL` > `.ghibli/last_model` > picker
- 第二次之後直接沿用上次選的 model（使用者不必每次重選）
- 對話過程把 agent 呼叫的 tool 即時顯示，讓等待時間有意義
- 退出時顯示 session id + resume 指令；空 session 不留垃圾
- Vertex AI 作為 picker 的顯式選項，onboarding 引導使用者跑 ADC
- Project-local 狀態（`sessions.db`、`last_model`）放 `<cwd>/.ghibli/`，一個 repo 一套
- 完全向後相容：`--model` bypass、eval pipeline、非 TTY 場景 100% 不受影響
- Gemma-4 作為 CLI 一等公民，走 LiteLLM（與 eval 對齊）

### Non-Goals

- **不**持久化每個 session 當時用的 model（只記全域最後一次）
- **不**在 onboarding 內做 API key 線上 validation
- **不**引入 `questionary` / `InquirerPy` 等互動 UI 依賴
- **不**改動 `evals/` 下任何檔案
- **不**從 shell / home 層級讀 `.env`

## Decisions

### Picker logic 放在獨立模組 `src/ghibli/picker.py`

**選擇**：`src/ghibli/picker.py` 對外暴露 `choose_model() -> str`（必回一個 model identifier、缺 credential 時自動轉 onboarding）、`read_last_model() -> str | None`、`write_last_model(identifier: str) -> None`、`append_env_var(...)`。`cli.py` 只負責 flag 解析與 orchestration。

**理由**：prompt 流程（選單、`.env` 寫入、last_model 持久化）與 Typer CLI 解耦，單元測試不需透過 `CliRunner` 就能覆蓋所有分支。

### 互動 UI 用 numbered choice（`typer.prompt` + 手寫選單）

**選擇**：列 `1) Gemini 2.5 Flash (API Key)` / `2) Gemini 2.5 Flash (Vertex AI)` / …，讀 `typer.prompt("Select", default=1, type=int)`。不用 arrow-key navigation。

**理由**：零新依賴；Rich + Typer 已有；所有終端（含 CI log、`screen`、`tmux`、SSH session）都能工作；無障礙閱讀器友善。

### Gemma-4 走 LiteLLM，`agent.py` 加 `gemini:<slug>` 前綴

**選擇**：`chat()` routing 加第三分支 `ghibli_model.startswith("gemini:")`，走 `litellm.completion(model=f"gemini/{slug}", api_key=GEMINI_API_KEY)`。Picker 選 Gemma 送 `gemini:gemma-4-26b-a4b-it`。

**理由**：`evals/models.py` 已驗證此路徑對 Gemma 可行；`google-genai` native SDK 對 Gemma function calling 支援度未驗證，硬用風險高。

### Tool call 可視化用 callback，不動 `chat()` 回傳型別

**選擇**：`agent.chat()` 加 keyword-only `on_tool_call: Callable[[str, dict], None] | None = None`。`cli.py` 傳入 callback 以 Rich 印 `→ {name}({args})`；`evals/` 不傳、行為不變。

**理由**：`chat() -> str` 契約不變、既有測試不動；callback 內部例外 try/except 包住，callback bug 不弄壞 chat loop。

### `.env` 寫入 append-only、既有 key 不覆蓋

**選擇**：`append_env_var(key, value, env_path=None)` 三分支——檔案不存在 → 建、存在無 key → append（補前置 `\n` 若需要）、存在有 key → 不動檔並拋 `SessionError`。UTF-8、明確 `"\n"`。

**理由**：使用者可能手動維護 `.env`，靜默覆蓋會毀掉 intent。顯式報錯 + 手動編輯指引最安全。

### 空 session 退出時清除

**選擇**：`cli.py` 結束對話時 `sessions.count_turns(session_id)`；若為 0 呼叫 `sessions.delete_session(session_id)`。

**理由**：不改 `create_session()` 或 `append_turn()` 契約，既有 session 測試不受影響。

### Model 解析優先順序（redesign 核心決策）

**選擇**：CLI main 按以下順序決定 `model`：

```
1. --model <id>（顯式）
2. GHIBLI_MODEL 環境變數
3. picker.read_last_model() → .ghibli/last_model 內容
4. 以上全落空 → picker.choose_model()（互動選 + 自動 write_last_model）
```

若 `--model-picker` flag 被設，**跳過 1/2/3**，強制走 4；且 `choose_model()` 照常寫回 `.ghibli/last_model`。

**理由**：顯式優先順序徹底排除 silent fallback；使用者能清楚預測當次跑哪個 model。`--model-picker` 是「想換 model」的顯式入口，解耦「跳過 picker」（= 傳 `--model`）與「我要重選」（= `--model-picker`）。

**替代方案**：保留 `gemini-2.5-flash` 為 fallback——被拒絕：初次 dogfood 顯示 silent default 讓使用者誤以為 picker 壞掉（明明沒設 key 卻進對話）。

### Last-model 持久化位置：`<cwd>/.ghibli/last_model`

**選擇**：Plain text 檔案，一行（`openai:gpt-4o-mini` 之類）。放 project root 的 `.ghibli/` 目錄。

**理由**：
- **Project-local**：一個 repo 一套設定，切 repo 不被上次的選擇干擾。符合「使用者在不同專案想用不同 model」的自然期望。
- **Plain text + 單行**：零 parsing 複雜度，`read_text().strip()` / `write_text(f"{id}\n")` 搞定。
- **`.gitignore` 包含 `.ghibli/`**：避免誤 commit 個人配置到 repo。

**替代方案**：`~/.ghibli/config.json` 跨專案全域——被拒絕：使用者在 MacOS / Linux / Windows 的 home 路徑不同，維運複雜；且跨專案共享反而強迫所有專案用同一個 model。

### SQLite session DB 搬至 `<cwd>/.ghibli/sessions.db`

**選擇**：`sessions.DB_PATH` 改為 `Path.cwd() / ".ghibli" / "sessions.db"`；首次使用自動建 `<cwd>/.ghibli/` 目錄。

**理由**：
- 與 `last_model` 共處同目錄，一個 `.ghibli/` 統管 project-local state
- 跨平台不依賴 home directory（Windows 沒有一致的 `~/.xxx` 慣例）
- 一個 repo 一套 session 歷史，避免不同專案的對話混在同一個 DB
- `.gitignore` 一次加 `.ghibli/` 搞定（比加 `~/.ghibli/` 的說明簡單）

**替代方案**：保留 `~/.ghibli/sessions.db`——被拒絕：原本就是 arbitrary 的選擇；project-local 對使用者心智模型更自然。

**Migration 成本**：舊 home 下的 session 歷史不自動搬。Dogfood 使用者基本上沒歷史 session，可接受。

### Vertex AI 作為 picker 獨立選項 + onboarding 走 gcloud ADC

**選擇**：Picker 列 5 個選項，其中 Gemini 2.5 Flash 分 (API Key) 與 (Vertex AI) 兩項。Vertex AI onboarding 流程：

```
[使用者選 Vertex AI]
Vertex AI uses Application Default Credentials (ADC).
Step 1: Run `gcloud auth application-default login` in another terminal.
        Press Enter when done.
Step 2: Paste your GCP Project ID:
Step 3 (optional): Paste your Vertex AI location [us-central1]:
```

寫 `GOOGLE_CLOUD_PROJECT`（+ 選用 `GOOGLE_CLOUD_LOCATION`）到 `.env`，不 prompt API key。

**理由**：
- 原本「選 Gemini + 有 `GOOGLE_CLOUD_PROJECT` 就走 Vertex」是隱式，使用者不知道自己選了什麼
- 顯式選項讓 Vertex 成為和其他 provider 對等的 first-class 選項
- ADC 用互動外 tool 設定（`gcloud` CLI）是既定事實，我們只提供指引而不試圖自動化

### 移除環境變數 provider 偵測

**選擇**：picker 的 `_PROVIDERS` 直接列 5 個選項，不再有 `env_any` 欄位、不再過濾「是否已配置」。選完再進入 onboarding 判斷缺不缺 credential。

**理由**：
- dogfood 顯示環境變數偵測會被 shell / `~/.env` / 上層目錄污染，造成不可預期的 UX
- 顯式選擇 + onboarding 的路徑對使用者的心智模型更清晰：「我選誰 → 缺什麼就幫我補」

### Picker 觸發條件：`--model-picker` 或（無 `--model` + 無 `GHIBLI_MODEL` + 無 `last_model`）

**選擇**：原本「TTY + 無 `--model`」的判定改為上述新條件。非 TTY 時若沒有任何 model 來源，仍會拋錯（而非 silent fallback）。

**理由**：顯式優先順序的自然結果；不該讓非 TTY 情境因為沒 TTY 而 silently 選錯 model。

### `.env` 只讀 `<cwd>/.env`，不往上找

**選擇**：`cli.py` 的 `load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)` 明確指定路徑，避免 python-dotenv 預設 `find_dotenv()` 走 parent directories。

**理由**：dogfood 踩到的真實 bug——`~/.env` 的 `GOOGLE_CLOUD_PROJECT` 污染 picker 判斷。明確指定路徑徹底排除。

## Risks / Trade-offs

- [Picker 5 個選項每次看起來多——尤其單人使用只用 1 個 provider] → Mitigation: 有了 `.ghibli/last_model`，真正顯示 picker 的時機只有「第一次使用」與「`--model-picker`」，平時看不到
- [Vertex AI onboarding 要求使用者離開 terminal 去跑 `gcloud` 指令] → Mitigation: 流程中明確提示 + 等待 Enter 確認；不勉強在 picker 內嵌 gcloud login 邏輯
- [`.ghibli/sessions.db` project-local 意味著換 repo 就失去 session 歷史] → 這是設計意圖，文件要寫清楚
- [現有 home 下的 `~/.ghibli/sessions.db` 不自動搬] → 接受：dogfood 階段沒有重要歷史；README 提醒「可手動複製」
- [Rich spinner 干擾 `typer.prompt`] → Mitigation: 只在 `agent.chat` 週邊啟動 spinner
- [`on_tool_call` callback 例外] → Mitigation: `_safe_invoke_callback` try/except 包住，寫 stderr 不重拋

## Migration Plan

本 change 無資料 schema 遷移。但涉及 **DB_PATH 改動**，對既有 session 的相容策略如下：

1. **先寫新 DB_PATH 與 auto-create dir**（`sessions.py`），不動既有 home 下的 db——既有使用者 `~/.ghibli/sessions.db` 保留不動，新 repo 用新位置
2. **README 加一小節** `Migrating existing sessions`：如果你原本在 home 有 session 想搬到 repo，`mv ~/.ghibli/sessions.db <repo>/.ghibli/sessions.db` 即可。對 dogfood 使用者 basically 零影響
3. **landing 順序**（降低回歸風險）：
   - (a) 改 `sessions.DB_PATH`，測試用 monkeypatch 覆蓋
   - (b) 加 `picker.read_last_model` / `write_last_model` + 測試
   - (c) 移除 picker 的環境變數偵測 + 改為 5 固定選項 + 測試
   - (d) 擴充 `run_onboarding` 支援 Vertex + 測試
   - (e) `cli.py` 改 model 解析優先順序 + 加 `--model-picker` flag + 測試
   - (f) `agent.py` 移除 `gemini-2.5-flash` silent default + 測試
   - (g) `.gitignore` / README / CLAUDE.md / `.env.example` 收尾
4. 每步跑 `uv run pytest`，紅了 `git reset` 單階段

## Open Questions

- 若 `<cwd>` 不是 git repo（使用者隨意 cd 一個目錄然後跑 `ghibli`），`.ghibli/` 會在那裡冒出來。要不要警告？傾向：不警告，這就是 project-local 的代價。
- `last_model` 檔案格式要不要保留擴充空間（例如 TOML、記錄 `last_model` 與未來可能的 `default_json_output`）？目前需求只有一個值，純文字最省事。未來若有 2+ 個設定再改成 JSON 不會造成使用者明顯困擾。
