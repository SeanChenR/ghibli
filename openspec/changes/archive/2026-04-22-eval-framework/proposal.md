## Why

ghibli Phase 1 已完成核心功能，但自然語言理解層（Gemini Function Calling）從未針對邊緣案例做系統性測試。在進入 Phase 2 強化之前，需要先找出哪些輸入類型會失敗、失敗的原因，以及哪些問題是根本上難以解決的，才能決定 Phase 2 的優先順序。

## What Changes

- 新增 `evals/queries.yaml`：30 條分類測試案例，涵蓋模糊輸入、錯別字、矛盾條件、多語言（日文、韓文）、多步驟查詢五個類別
- 新增 `evals/run_evals.py`：執行器，逐一跑每條查詢、記錄實際呼叫的 tool 與回應、標記 pass/fail/error
- 新增 `evals/results.json`：每次執行的結果快照（commit 進 repo，作為 Phase 3 ground truth 的前置資料）
- 更新 `README.md`：新增「已知限制」章節，解釋哪些失敗案例從根本上難以解決及原因

## Non-Goals

- 不修改任何 `src/ghibli/` 的核心邏輯（找缺陷，不修缺陷）
- 不引入 LiteLLM 或其他模型（Phase 3 工作）
- 不建立 CI 自動化 eval（需要真實 API key，不適合 CI）
- 不對每條查詢定義唯一「正確答案」（模糊查詢本來就沒有唯一答案，記錄行為即可）

## Capabilities

### New Capabilities

- `eval-harness`：定義 eval 查詢格式、執行器邏輯、結果記錄 schema，以及 README 已知限制文件

### Modified Capabilities

（無）

## Impact

- 新增：`evals/queries.yaml`、`evals/run_evals.py`、`evals/results.json`
- 修改：`README.md`（新增已知限制章節）
- 依賴：需要設定 `GEMINI_API_KEY` 才能執行 eval runner
