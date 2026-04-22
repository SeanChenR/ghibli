# Project: ghibli（GitHub Intelligence Bridge）

自然語言 → Gemini Function Calling → GitHub REST API → 格式化輸出的 CLI 工具。
詳細規格見 `specs/`（mission、roadmap、tech-stack）。

## 關鍵架構決策

- **LLM**：`google-genai` SDK（非 `google-generativeai`），模型 `gemini-2.5-flash`
- **SDK 注意**：`tools` 必須放在 `config=GenerateContentConfig(tools=..., automatic_function_calling=AutomaticFunctionCallingConfig(disable=True))` 裡，SDK >= 1.0 不接受直接 kwarg
- **認證**：優先 `GEMINI_API_KEY`；否則 `GOOGLE_CLOUD_PROJECT` + `GOOGLE_CLOUD_LOCATION` + ADC
- **互動模式**：對話 loop（非單次 pipeline）；Gemini 自行決定是否呼叫 GitHub tool
- **Session 歷史**：每輪結束後以 `sessions.append_turn()` 存 user + assistant；下一輪開頭以 `sessions.get_turns()` 重建 Gemini `contents`
- **Session 儲存**：SQLite `~/.ghibli/sessions.db`，`sessions` + `turns` 兩張表
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
