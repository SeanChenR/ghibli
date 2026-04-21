## Context

`cli.py` 是 ghibli 的使用者介面層。`project-scaffold` 建立了只有空 callback 的骨架；此 change 實作完整的互動對話 CLI，包含所有 flags、session 管理、以及 conversation loop。

這個 change 是純粹的 CLI 層，不包含 LLM 或 GitHub API 邏輯——這些由後續 `github-tools`、`github-api-client` change 實作。此 change 完成後，`main()` 的 agent 呼叫以 stub 回應代替。

## Goals / Non-Goals

**Goals:**

- 宣告所有 CLI flags（`--session`、`--list-sessions`、`--json`、`--version`）
- 實作 conversation loop（多輪輸入、空行或 EOF 退出）
- session 建立與載入（呼叫 `sessions` 模組，不自行存取 DB）
- 優雅處理 `Ctrl+C`、`Ctrl+D`（exit code 0）
- 未知 session ID 回傳 exit code 1

**Non-Goals:**

- 不整合 Gemini agent（stub 回應，`github-tools` change 負責）
- 不實作 Rich 格式化（`output-formatter` change 負責）
- 不直接操作 SQLite（`session-manager` change 負責）

## Decisions

### Typer `@app.callback()` 而非 `@app.command()`

使用 `@app.callback()` + `invoke_without_command=True` 讓 `ghibli`（無子指令）直接啟動主功能，而非顯示 help。

**理由：** ghibli 是單指令工具，沒有子指令。`@app.command()` 在無子指令時會觸發 Typer 要求子指令的錯誤；`@app.callback()` 搭配 `Typer(invoke_without_command=True)` 是 Typer 官方推薦的單指令模式。

**捨棄方案：** `@app.command()` — 在 `ghibli --version` 等 eager flag 搭配上行為不一致。

### `--version` 使用 eager callback 而非 flag 檢查

`--version` 以 `typer.Option(callback=_version_callback, is_eager=True)` 實作，callback 內 `raise typer.Exit()`。

**理由：** Eager flag 在 Typer 解析其他 option 之前就執行，確保 `ghibli --version --session foo` 仍能正常印出版本並退出，不會因為其他 flag 驗證而報錯。

### `typer.prompt` 加 `default=""` 以接受空行輸入

Conversation loop 的輸入用 `typer.prompt("You", prompt_suffix="> ", default="", show_default=False)`。

**理由：** Click（Typer 底層）的 `prompt` 預設不接受空字串——空行時會重新要求輸入，直到輸入耗盡觸發 `click.exceptions.Abort`，造成 exit code 1。加上 `default=""` 後，空行直接被接受並回傳 `""`，再由 loop 邏輯判斷退出。

**捨棄方案：** 用 `sys.stdin.readline()` 直接讀取——不走 Click 的 prompt 格式，在 CliRunner 測試中行為不一致。

### 捕捉 `click.exceptions.Abort` 而非只捕捉 `EOFError`

EOF（`Ctrl+D`）在 CliRunner 中會讓 `click.prompt` 拋出 `click.exceptions.Abort`（非 `EOFError`），Typer 預設處理 `Abort` 會印 "Aborted!" 並 exit 1。

**理由：** 為讓 EOF 也能優雅退出（exit 0、印 "Bye!"），必須在 prompt 呼叫外層捕捉 `click.exceptions.Abort`，先處理再讓 Typer 接管。

## Risks / Trade-offs

- **[stub 回應]** Conversation loop 目前印 `[stub] {user_input}`，使用者跑 `ghibli` 還不能真正查詢 GitHub → `github-tools` change 完成後替換為 `agent.chat()` 呼叫
- **[session 沒有 title]** 新 session 沒有 title，`--list-sessions` 顯示空白 title → 後續可在 conversation 結束時以第一句話作為 title 更新
- **[CliRunner 與真實 TTY 行為差異]** `typer.prompt` 在 CliRunner（非 TTY）環境下行為有細微差異（Abort vs EOFError）→ 已透過捕捉 `click.exceptions.Abort` 解決，但若未來改用其他輸入方式需重新驗證

## Open Questions

（無）
