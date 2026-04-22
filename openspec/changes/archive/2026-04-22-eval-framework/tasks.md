## 1. 測試 — query catalog schema 驗證（Red）

- [x] 1.1 [P] 在 `tests/unit/test_eval_queries.py` 寫 `test_queries_yaml_loads_without_error()`：以 `yaml.safe_load` 讀取 `evals/queries.yaml`，斷言結果為 list 且長度 ≥ 30（對應：query catalog defines categorized test cases）
- [x] 1.2 [P] 在 `tests/unit/test_eval_queries.py` 寫 `test_each_query_has_required_fields()`：對每個 entry 斷言有 `id`、`category`、`query`、`expected_behavior`、`difficulty`、`notes` 六個 key 且均非空（對應：each entry has required fields）
- [x] 1.3 [P] 在 `tests/unit/test_eval_queries.py` 寫 `test_category_values_are_valid()`：對每個 entry 斷言 `category` in `{"fuzzy", "typo", "contradiction", "multilingual", "multi_step"}`，且每個 category 至少 5 條（對應：category values are valid）

## 2. 實作 — 建立 evals/queries.yaml（Green）

<!-- 查詢格式：YAML 而非 Python hardcode；五個測試類別及各 6 條查詢 -->
- [x] 2.1 建立 `evals/queries.yaml`，內含 30 條測試案例（每類別 6 條）：
  - **fuzzy（6 條）**：「找個好用的前端框架」、「最近很紅的 AI 工具」、「幫我找個 Python 好用的 library」、「找個有趣的開源專案」、「想看看最受歡迎的東西」、「有沒有什麼值得學習的 repo」
  - **typo（6 條）**：「pytohn 最多星星的 repo」、「javascrpit 框架」、「torvalds 的 linus repo」、「facebook/reakt 的 issues」、「找 djangoo 的 release」、「microsfot/vscode 的 PR」
  - **contradiction（6 條）**：「找 star 超過 100 萬的 repo」、「列出一個同時是 open 又是 closed 的 PR」、「找一個 2090 年建立的 repo」、「搜尋沒有任何 commit 但有 100 萬 star 的 repo」、「找一個 fork 數比 star 數多 1000 倍的 repo」、「列出 0 個 follower 但 following 100 萬人的 user」
  - **multilingual（6 條）**：`"Pythonのリポジトリを検索して"` (日文)、`"파이썬 레포지토리 검색해줘"` (韓文)、`"找一下 tensorflow 的 issues"` (繁中)、`"tensorflow issues 찾아줘"` (韓文)、`"torvaldsのプロフィールを見せて"` (日文)、`"最も星が多いJavaScriptフレームワーク"` (日文)
  - **multi_step（6 條）**：「找最多 star 的 Python repo，然後告訴我它最新的 release」、「查一下 torvalds 的 GitHub 個人資料，然後看看他的 linux repo 有什麼 open issue」、「搜尋 React 相關 repo，找出 star 最多的那個，再列出它的最新 3 個 release」、「先找 microsoft/vscode 的資訊，再看它有哪些 open PR」、「查詢 anthropic 的使用者資訊，再列出 anthropic/claude 這個 repo 的 releases」、「找 star 最多的 Go web framework，然後看看它最近的 issue」
- [x] 2.2 執行 `pytest tests/unit/test_eval_queries.py -v --no-cov`，確認 3 個測試全部通過

## 3. 測試 — runner 邏輯單元測試（Red）

- [x] 3.1 [P] 在 `tests/unit/test_eval_runner.py` 寫 `test_run_single_query_pass()`：mock `agent.chat` 回傳 `"Found repos"` + mock `ghibli.tools.search_repositories` 記錄呼叫，呼叫 `run_query(entry, session_id)` 函式，斷言回傳 dict 的 `status == "pass"`、`tools_called == ["search_repositories"]`、`response_preview == "Found repos"`（對應：results file captures structured run output、runner instruments agent to capture tool calls）
- [x] 3.2 [P] 在 `tests/unit/test_eval_runner.py` 寫 `test_run_single_query_error()`：mock `agent.chat` 拋出 `ToolCallError("boom")`，呼叫 `run_query(entry, session_id)`，斷言 `status == "error"`、`error_message == "boom"`、`tools_called == []`（對應：runner handles agent exceptions without stopping）
- [x] 3.3 [P] 在 `tests/unit/test_eval_runner.py` 寫 `test_run_single_query_fail()`：mock `agent.chat` 回傳空字串 `""`，呼叫 `run_query(entry, session_id)`，斷言 `status == "fail"`（對應：status values reflect actual outcome）
- [x] 3.4 [P] 在 `tests/unit/test_eval_runner.py` 寫 `test_results_are_appended()`：以暫存目錄建立 `results.json`，呼叫 `append_run(results_path, run_object)` 兩次，斷言 `results.json` 內陣列長度為 2（對應：results file is appended on each run）
- [x] 3.5 [P] 在 `tests/unit/test_eval_runner.py` 寫 `test_category_filter()`：mock `load_queries()` 回傳含 `fuzzy` 與 `typo` 的 entries，呼叫 `filter_queries(entries, category="typo")`，斷言只回傳 `typo` 的 entries（對應：runner filters by category）

## 4. 實作 — evals/run_evals.py（Green）

<!-- 執行器：直接呼叫 agent.chat()，不繞過 Gemini；結果儲存：append 模式，保留歷史；pass/fail 判斷標準；Eval runner executes queries against real agent -->
- [x] 4.1 建立 `evals/run_evals.py`，實作以下函式與 CLI 入口：
  - `load_queries(path: str) -> list[dict]`：以 `yaml.safe_load` 讀取 queries.yaml
  - `filter_queries(queries: list[dict], category: str | None) -> list[dict]`：若 category 為 None 回傳全部，否則過濾
  - `run_query(entry: dict, session_id: str) -> dict`：呼叫 `agent.chat(entry["query"], session_id, False)`，以 `unittest.mock.patch` instrumentation 捕捉 `ghibli.tools` 各函式被呼叫時的名稱（patch 後仍呼叫原始函式），記錄 `status`/`tools_called`/`response_preview`/`error_message`/`duration_seconds`
  - `append_run(results_path: str, run: dict) -> None`：讀取現有 JSON（若不存在則 `[]`），append run，寫回
  - `main(category: str | None = None)`：呼叫上述函式，印出每條查詢的 id 與 status，最後印出 summary（pass/fail/error 數量）
  - CLI 入口：`if __name__ == "__main__": typer.run(main)` 支援 `--category` 可選參數
- [x] 4.2 執行 `pytest tests/unit/test_eval_runner.py -v --no-cov`，確認 5 個測試全部通過

## 5. 實作 — 執行真實 eval 並記錄結果

- [x] 5.1 Eval runner executes queries against real agent：執行 `python evals/run_evals.py`（需設定 `GEMINI_API_KEY`），確認 `evals/results.json` 被建立，內含 1 個 run 物件、30 條 result
- [x] 5.2 檢視 `results.json`，將每條 `status == "fail"` 或 `status == "error"` 的查詢手動標注 `notes`（在 queries.yaml 對應 entry 補充觀察），記錄哪些類別的失敗率最高

## 6. 實作 — README 已知限制章節

- [x] 6.1 在 `README.md` 新增「已知限制」章節，說明三類根本困難：(1) **模糊輸入**：查詢沒有明確 API 參數對應，Gemini 只能猜測搜尋詞，結果因問法而異；(2) **矛盾條件**：GitHub API 本身不驗證邏輯可能性，會回傳空結果而非錯誤，Gemini 無法在呼叫前偵測矛盾；(3) **非中文多語言**：Gemini 支援多語言但 ghibli 僅以繁中/英文測試，日文/韓文的 function calling 行為未驗證（對應：README documents known limitations）

## 7. 驗證

- [x] 7.1 執行 `pytest tests/unit/ -v --cov=src/ghibli --cov-report=term-missing`，確認所有 unit tests 通過且覆蓋率 ≥ 80%
- [x] 7.2 執行 `ruff check src/ evals/`，確認無 lint 錯誤
