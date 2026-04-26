# Project: ghibli（GitHub Intelligence Bridge）

自然語言 → Gemini Function Calling → GitHub REST API → 格式化輸出的 CLI 工具。
詳細規格見 `specs/`（mission、roadmap、tech-stack）。

## 關鍵架構決策

- **LLM**：`google-genai` SDK（非 `google-generativeai`）+ LiteLLM 多後端，**無 silent default**——呼叫 `agent.chat()` 若沒拿到 model（flag / env / picker 全落空）會拋 `ToolCallError`
- **Model 解析優先順序**（在 `cli.py` 決定）：
  1. `--model <id>`
  2. `GHIBLI_MODEL` env var
  3. `<cwd>/.ghibli/last_model`（picker 選完自動寫回）
  4. `picker.choose_model()` 互動選（含 onboarding）
  5. 全落空 → `typer.Exit(code=1)` 並印錯誤；`--model-picker` flag 強制走第 4 步
- **多後端路由**：`agent.chat()` 以 prefix 決定——`openai:<slug>` / `ollama:<slug>` / `gemma:<slug>` 走 LiteLLM，無 prefix 走 Gemini 原生 SDK；`gemma:` 專給 Gemma-4 等 Gemini API 上的 open-weight 模型（LiteLLM model id 內部仍是 `gemini/<slug>`）
- **Picker 設計**：一律顯示 5 個 provider（不看環境變數偵測），使用者選完檢查該 provider 的 credential env var 是否 set；不 set 則跑 provider-specific onboarding（API Key 類 prompt hidden input，Vertex 類指引 `gcloud auth application-default login` + project id）寫入 `.env`
- **`.env` 只讀 cwd**：`load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)` 明確指定，避免 python-dotenv 預設往上找到 `~/.env`
- **SDK 注意**：`tools` 必須放在 `config=GenerateContentConfig(tools=..., automatic_function_calling=AutomaticFunctionCallingConfig(disable=True))`，SDK >= 1.0 不接受直接 kwarg
- **認證**：native SDK 路徑先看 `GEMINI_API_KEY`，否則 `GOOGLE_CLOUD_PROJECT` + ADC；LiteLLM 路徑各自讀對應 `*_API_KEY`
- **互動模式**：對話 loop；Gemini / LiteLLM 自行決定是否呼叫 tool
- **Tool 可視化**：`agent.chat(on_tool_call=cb)` 在每次 dispatch 前呼叫 callback，CLI 傳入印 `→ tool(args)` 讓使用者看到推理過程
- **Session 歷史**：每輪結束後 `sessions.append_turn()` 存；下一輪開頭 `sessions.get_turns()` 重建 `contents`；退出時 0 turns 自動刪 session
- **Project-local 狀態**：`<cwd>/.ghibli/` 同時放 `sessions.db`（SQLite）與 `last_model`（純文字一行）；`.gitignore` 已包含 `.ghibli/`。每個 repo 一套獨立狀態，跨平台不依賴 home directory 結構
- **套件管理**：`uv`，Python 3.12，src layout（`src/ghibli/`）

## Phase 1 完成狀態

所有 6 個 Spectra change 已全部 archive：
1. ✅ `project-scaffold` — 專案骨架、pyproject.toml、exceptions
2. ✅ `session-manager` — SQLite sessions/turns CRUD
3. ✅ `github-api-client` — httpx GitHub REST API 執行層
4. ✅ `cli-entry-point` — Typer CLI + 對話 loop
5. ✅ `github-tools` — Gemini Function Calling agent + 6 tools
6. ✅ `output-formatter` — Rich Markdown / JSON 輸出，session history 串接

## Phase 2 Eval 架構

### Query 設計
- **30 題 = 6 情境 × 5 題**：`discover` / `compare` / `debug_hunt` / `track_vuln` / `follow_up` / `refuse`
- Category 基於「使用者在做什麼」而非「測試哪個 failure mode」——圍繞真實 AI-dev 場景（OpenClaw、axios 供應鏈事件、React CVE、LiteLLM compromise、Qdrant deep dive 等）
- Multi-label `failure_modes` tag（7 個）用於 cross-category 失敗模式分析：`multilingual` / `ambiguous_input` / `messy_phrasing` / `outdated_assumption` / `typo` / `qualifier_mapping` / `temporal_reasoning`

### Judge 邏輯（`evals/judge.py`）
- **Multiset subset**：檢查每個 required tool 被 call 次數 ≥ 要求次數，**順序不管**。理由：data-flow 自然強制順序（search 必在 get_repository 前因為後者需前者 owner/repo），硬要求 sequence 是 artificial discipline
- **Refuse scenario**：`tool: refuse` sentinel + `valid_parts_tool_sequence`（正常子問題該 call 的工具）+ `refusal_keywords`（response 必須包含）——測模型是否能「正常部分答，不可行部分拒」
- **Pass 條件**：normal = tool_match AND sequence_match；refuse = sequence_match AND flagged_refusal

### Ground Truth 設計原則
- 放寬 `get_repository` 當它 functionally redundant：例如 `search_issues q='repo:x/y keyword'` 已 scope 到特定 repo，不需 get_repository anchor
- 保留 `get_repository` 當它真的需要：compare N-way、follow_up deep-dive、list_releases 前的版本 anchor

### Prompt 設計（`src/ghibli/prompt.py`）
- **Scope reframing**：ghibli 是「GitHub-powered technical research assistant」——回答技術問題都 route 到 GitHub 資料，不限「GitHub 實體查詢」
- **Query-pattern → tool mapping**：X vs Y → get_repository × N；升級 → list_releases；「有人遇過嗎」→ search_issues；活躍度 → list_commits / list_releases 等
- **Named repo first**：指名 repo 必先 get_repository anchor（防 Gemini Flash 跳過步驟的常見失誤）
- **Partial refusal**：混合 valid + impossible 的 query 要答正常部分 + 拒絕不可行部分，first-principles reasoning 判斷矛盾（不列具體 impossibility 枚舉，防 eval leakage）
- **嚴禁鏡射 eval 資料集**：prompt 不包含 eval query 的具體 repo / keyword / impossibility 枚舉。歷史教訓詳見 `memory/prompt_eval_leakage_rule.md`

### Harness（`evals/models.py` / `evals/run_evals.py`）
- **Retry 覆蓋**：`RateLimitError`（解析 retry-after） / `ServiceUnavailableError` / `Timeout` / `ConnectionError` 都有 exponential backoff（最多 5 次）
- **Verbose tool output**：每次 tool call 印 `→ tool(args)` + `← result preview`，eval 看起來像 CLI
- **tool_calls_detail 存入 result**：每 query 記錄每次 call 的 tool name + args + result preview，可驗證 grounding（回答是否基於真實搜尋結果）

### Model registry（`_MODEL_CONFIG` in `evals/models.py`）
- **最終選的 3 個**：`gemini-vertex`（Flash, Vertex AI）/ `gemma4`（open-weight via Gemini API）/ `gpt51`（GPT-5.1，reasoning=none default）
- **試驗過的**：`gpt5-mini`（reasoning=medium default 太慢，90+ min/30 題）、`gpt4o`（73% 但不在最終）、`gemini-vertex-pro`（43% 反而比 Flash 差）、`gemini`（API key 路徑，遇 503 crash）
- **Credentials**：Gemini Vertex 用 ADC + `GOOGLE_CLOUD_PROJECT`；Gemma4 用 `GEMINI_API_KEY`（free tier 有 RPM 無 TPM 限制）；OpenAI 系用 `OPENAI_API_KEY`

### Results 組織
- `evals/results/{model}.json` — 最終 3 model 的 per-model run history（append 式，最新 run 在最後）
- `evals/results-archive/` — 試驗過但不是最終的 model 結果（gpt4o、gemini-vertex-pro、gemini 等）
- `evals/results-legacy*.json` — pre-restructure 舊 eval 架構的歷史資料
- `evals/compare_models.py` 從 `evals/results/*.json` 聚合，不讀 archive

---

<!-- SPECTRA:START v1.0.2 -->

# Spectra Instructions

This project uses Spectra for Spec-Driven Development(SDD). Specs live in `openspec/specs/`, change proposals in `openspec/changes/`.

## Use `/spectra-*` skills when:

- A discussion needs structure before coding → `/spectra-discuss`
- User wants to plan, propose, or design a change → `/spectra-propose`
- Tasks are ready to implement → `/spectra-apply`
- There's an in-progress change to continue → `/spectra-ingest`
- User asks about specs or how something works → `/spectra-ask`
- Implementation is done → `/spectra-archive`
- Commit only files related to a specific change → `/spectra-commit`

## Workflow

discuss? → propose → apply ⇄ ingest → archive

- `discuss` is optional — skip if requirements are clear
- Requirements change mid-work? Plan mode → `ingest` → resume `apply`

## Parked Changes

Changes can be parked（暫存）— temporarily moved out of `openspec/changes/`. Parked changes won't appear in `spectra list` but can be found with `spectra list --parked`. To restore: `spectra unpark <name>`. The `/spectra-apply` and `/spectra-ingest` skills handle parked changes automatically.

<!-- SPECTRA:END -->
