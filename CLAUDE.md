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

## Phase 1 完成狀態（2026-04-22）

所有 6 個 Spectra change 已全部 archive：
1. ✅ `project-scaffold` — 專案骨架、pyproject.toml、exceptions
2. ✅ `session-manager` — SQLite sessions/turns CRUD
3. ✅ `github-api-client` — httpx GitHub REST API 執行層
4. ✅ `cli-entry-point` — Typer CLI + 對話 loop
5. ✅ `github-tools` — Gemini Function Calling agent + 6 tools
6. ✅ `output-formatter` — Rich Markdown / JSON 輸出，session history 串接

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
