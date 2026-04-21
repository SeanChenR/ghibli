## 1. 測試 — 單元測試（Red）

- [x] 1.1 [P] 在 `tests/unit/test_output.py` 設定 `rich.console.Console(file=io.StringIO())` 的輸出捕捉 pattern；寫 `test_render_text_accepts_nonempty_text()` — 呼叫 `render_text("hello", json_output=False)`，斷言不 raise 任何例外；寫 `test_render_text_empty_string_prints_placeholder()` — 呼叫 `render_text("", json_output=False)`，斷言 stdout 含 `"(no response)"`（對應：render_text function accepts text and json_output flag）
- [x] 1.2 [P] 在 `tests/unit/test_output.py` 寫 `test_markdown_output_renders_text()` — 呼叫 `render_text("**bold**", json_output=False)`，斷言 stdout 非空（對應：Markdown output mode renders Rich Markdown）
- [x] 1.3 [P] 在 `tests/unit/test_output.py` 寫 `test_json_output_wraps_in_response_key()` — 以 `capsys.readouterr()` 捕捉，呼叫 `render_text("找到 3 個倉庫", json_output=True)`，斷言 stdout 含 `"response"` 且含 `"找到 3 個倉庫"`（不含 Unicode escape）（對應：JSON output mode renders response wrapped in JSON）

## 2. 實作（Green）

- [x] 2.1 在 `src/ghibli/output.py` 實作 `render_text(text: str, json_output: bool) -> None`：若 `text` 為空字串，以 `rich.print("(no response)")` 輸出並 return；若 `json_output=True`，以 `print(json.dumps({"response": text}, indent=2, ensure_ascii=False))` 輸出；否則以 `Console().print(Markdown(text))` 渲染 Markdown（對應：render_text function accepts text and json_output flag、Markdown output mode renders Rich Markdown、JSON output mode renders response wrapped in JSON）
- [x] 2.2 執行 `pytest tests/unit/test_output.py -v` 直到所有測試通過

## 3. 串接完整 pipeline（cli.py）

- [x] 3.1 修改 `src/ghibli/cli.py` 的 `main()` 函式中對話 loop：import `render_text` from `ghibli.output`；import `agent` from `ghibli.agent`（此 module 在 `github-tools` change 完成後提供）；在 loop 中以 `response = agent.chat(user_input, session_id, json_output)` 取代 stub 輸出，然後以 `render_text(response, json_output)` 顯示；以 try/except `GhibliError` 包裹整個 turn，捕捉時印出 `f"Error: {e}"` 並 continue（對應：conversation loop renders agent response each turn、GhibliError in one turn does not end the session）

## 4. 驗證

- [x] 4.1 執行 `pytest tests/unit/ -v --cov=src/ghibli --cov-report=term-missing` 確認所有單元測試通過且覆蓋率 ≥ 80%
- [x] 4.2 手動端對端測試：執行 `ghibli` 後輸入一個查詢，確認 Rich Markdown 輸出；再以 `ghibli --json` 確認 JSON 輸出
- [x] 4.3 執行 `ruff check src/` 確認整個 src/ 目錄無 lint 錯誤
