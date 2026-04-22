## 1. Ground Truth 標注（query catalog）

- [x] 1.1 [TDD-RED] 在 `tests/unit/test_eval_queries.py` 新增測試：驗證「every query entry carries a ground_truth annotation」— 每條 entry 有 `ground_truth.tool`（合法 tool 名之一）；`multi_step` 類的 entry 有 `ground_truth.tool_sequence` 且長度 ≥ 2；驗證「query catalog defines categorized test cases」— 30 條 entry 每條都有 ground_truth
- [x] 1.2 為 `evals/queries.yaml` 全部 30 條 entry 加入 `ground_truth` 欄位（ground truth 標注格式見 design.md）：`tool`（必填）、`params`（選填，key-value partial match）、`tool_sequence`（選填，僅 multi_step 類）
- [x] 1.3 [TDD-GREEN] 執行 `uv run pytest tests/unit/test_eval_queries.py -v`，確認 1.1 的新測試全部 pass

## 2. Tool Schema 轉換（OpenAI-compatible format）

- [x] 2.1 [TDD-RED] 在 `tests/unit/test_tool_schema.py` 新增測試：`get_openai_tool_schemas()` 確認「tool schemas are exported in OpenAI-compatible format」— 回傳 list 長度為 6；每個 dict 含 `type="function"`、`function.name`、`function.description`、`function.parameters`；name 集合等於六個合法 tool 名
- [x] 2.2 建立 `evals/tool_schema.py`，實作 `get_openai_tool_schemas() -> list[dict]`：遍歷 `ghibli.tools` 模組中的 6 個 function，從 docstring 取 description，從 type hints 組合 parameters JSON Schema，回傳 OpenAI tool schema dict list
- [x] 2.3 [TDD-GREEN] 執行 `uv run pytest tests/unit/test_tool_schema.py -v`，確認全部 pass

## 3. Judge 模組

- [x] 3.1 [TDD-RED] 建立 `tests/unit/test_judge.py`，測試「judge compares tool calls against ground truth」的五個情境：(a) tools_called 包含 ground_truth.tool → pass；(b) 不包含 → fail；(c) tool_sequence 正確順序 → sequence_match=True；(d) 順序錯誤 → False；(e) tools_called=[] → tool_match=False
- [x] 3.2 建立 `evals/judge.py`，實作 `judge(tools_called: list[str], ground_truth: dict) -> dict`：回傳 `tool_match`、`sequence_match`、`pass_`；sequence 比對採非連續子序列匹配
- [x] 3.3 [TDD-GREEN] 執行 `uv run pytest tests/unit/test_judge.py -v`，確認全部 pass

## 4. 多模型 Runner（models.py）— LiteLLM 多模型介面

- [x] 4.1 [P] [TDD-RED] 建立 `tests/unit/test_models.py`，mock LiteLLM 呼叫，測試「models.py exposes a unified chat interface for all supported models」：(a) model_name="gemini" → `gemini/gemini-2.5-flash`；(b) "gpt4o-mini" → `openai/gpt-4o-mini`；(c) "llama3" → `groq/llama-3.3-70b-versatile` + sleep(1)；(d) 缺 API key → ToolCallError 含 key 名
- [x] 4.2 [P] 在 `pyproject.toml` 加入 `litellm>=1.50.0`，執行 `uv sync`；在 `.env.example` 加入 `OPENAI_API_KEY` 與 `GROQ_API_KEY` 說明欄位
- [x] 4.3 建立 `evals/models.py`，實作 `chat_with_model(user_message: str, session_id: str, model_name: str) -> tuple[str, list[str]]`（litellm 多模型介面）：依 model_name 選 LiteLLM model ID；使用 `get_openai_tool_schemas()` 作為 tools；執行 agentic loop；llama3 每次 `time.sleep(1)`；回傳最終文字回覆與 tools_called
- [x] 4.4 [TDD-GREEN] 執行 `uv run pytest tests/unit/test_models.py -v`，確認全部 pass

## 5. run_evals.py 擴充

- [x] 5.1 [TDD-RED] 在 `tests/unit/test_eval_runner.py` 新增測試：確認「eval runner accepts a model selector flag」— `--model gpt4o-mini` 時 run_obj["model"]="gpt4o-mini"；確認「run accuracy is computed and stored」— run_obj 含 accuracy float；per-query result 含 judge_result.pass_；`--model unknown` 不寫 results.json
- [x] 5.2 修改 `evals/run_evals.py`：新增 `--model` typer.Option（預設 "gemini"，允許值 {"gemini","gpt4o-mini","llama3"}）；`run_query()` 依 model 路由到 `agent.chat` 或 `chat_with_model`；每筆 result 加 `judge_result`（呼叫 `judge(tools_called, entry["ground_truth"])`）；run_obj 加 `model` 與 `accuracy`（passed/total）；「results file captures structured run output」新增 accuracy 與 model 欄位
- [x] 5.3 [TDD-GREEN] 執行 `uv run pytest tests/unit/test_eval_runner.py -v`，確認全部 pass（含舊測試）

## 6. compare_models.py

- [x] 6.1 [TDD-RED] 建立 `tests/unit/test_compare_models.py`，確認「compare_models.py outputs a cross-model accuracy table」：(a) 含三模型 run → header + 3 data row；(b) accuracy 四捨五入百分比；(c) 缺 llama3 → 僅 2 row
- [x] 6.2 建立 `evals/compare_models.py`：讀 `evals/results.json`，group by model 取最新 run，計算整體與各類別 accuracy，輸出 Markdown 表格至 stdout；`uv run python evals/compare_models.py` 可直接執行
- [x] 6.3 [TDD-GREEN] 執行 `uv run pytest tests/unit/test_compare_models.py -v`，確認全部 pass

## 7. Eval 執行與 Prompt 迭代

- [x] 7.1 跑 Gemini baseline：`uv run python evals/run_evals.py --model gemini`，記錄 accuracy 與失敗 query ID
- [x] 7.2 跑 GPT-4o-mini：`uv run python evals/run_evals.py --model gpt4o-mini`，記錄 accuracy 與失敗 query ID
- [x] 7.3 跑 Llama 3：`uv run python evals/run_evals.py --model llama3`，記錄 accuracy 與失敗 query ID
- [x] 7.4 若任一模型 accuracy < 85%，針對失敗類別修改 `_SYSTEM_PROMPT`（`src/ghibli/agent.py`），重新跑該模型直到 ≥ 85%
- [x] 7.5 執行 `uv run python evals/compare_models.py`，確認三個模型輸出欄位完整

## 8. README Part 2 Write-up

- [x] 8.1 在 `README.md` 新增「Part 2 — Multi-Model Eval」章節：(a) 模型選擇理由（為何選這三個）；(b) 各模型初始 accuracy 與失敗模式；(c) prompt 迭代過程與前後效果；(d) eval 設計心得（ground truth 標注難點、judge 設計取捨）
