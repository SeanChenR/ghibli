## 1. Setup 與依賴

- [x] 1.1 [P] 加 `deepeval` 依賴到 `pyproject.toml`，跑 `uv lock` 解決版本衝突；驗證 `uv run python -c "import deepeval"` 成功
- [x] 1.2 [P] 在 `.gitignore` 加 `evals/synthesized-queries/*.json`（中間產物不入 git，僅 `findings.md` 入 git）

## 2. Semantic judge 主邏輯（TDD）

- [x] 2.1 為「Semantic judge layer evaluates stored responses without re-calling APIs」要求寫測試 `tests/unit/test_deepeval_judge.py`：載入假的 stored result fixture、mock DeepEval `evaluate()` 確保不真打 API、驗證 30 個 query 都被處理；接著實作 `evals/deepeval_judge.py` 的 stored result loader 與 per-query metric loop（即 design 的「DeepEval 跑 rejudge 模式（讀 stored response，不重打 API）」），讓測試通過
- [x] 2.2 為「Four metrics evaluate answer quality dimensions」要求與 design 的「4 個 metric 的選擇」決定寫測試：每個 query 都建立 `AnswerRelevancyMetric`、`FaithfulnessMetric`、`HallucinationMetric` 三個 instance；refuse 類額外建立 `GEval` 且 name 為 `Partial Refusal Quality`，非 refuse 類 partial_refusal=null 且 reason="N/A non-refuse"；實作 conditional metric 構造邏輯讓測試通過
- [x] 2.3 為「Four metrics evaluate answer quality dimensions」中 hallucination metric 的 retrieval_context 行為寫測試：`HallucinationMetric` 收到的 `context` 參數從 `tool_calls_detail` 抽出 `result_preview` 字串清單；實作抽取邏輯讓測試通過
- [x] 2.4 為「Judge LLM is configurable and decoupled from under-test model」要求寫測試（含 design 的「LLM judge 模型用 Gemini 2.5 Flash」決定）：env var `DEEPEVAL_JUDGE_MODEL` 未設時 default 為 `gemini/gemini-2.5-flash`、已設時用該值、輸出 JSON 的 `judge_model` 正確記錄；實作 judge model 解析邏輯讓測試通過
- [x] 2.5 為「Metric thresholds are explicit constants」要求寫測試：源碼包含 `ANSWER_RELEVANCY_THRESHOLD = 0.7`、`FAITHFULNESS_THRESHOLD = 0.7`、`HALLUCINATION_THRESHOLD = 0.7`、`PARTIAL_REFUSAL_THRESHOLD = 0.6` 四個 module-level 常數；實作這四個常數讓測試通過

## 3. 輸出 schema 與 async 配置

- [x] 3.1 為「Output JSON includes per-query verdicts and aggregate summary」要求與 design 的「結果儲存：`evals/results-deepeval/{model}.json`」決定寫測試：輸出 schema 含 `query_id`、`structural_pass`（從 input 複製）、`metrics` 物件（4 metric 各含 `score`/`passed`/`reason`）、`semantic_pass`（boolean）、`judge_disagreement`（`structural_pass != semantic_pass`），及 `summary` 欄位含 6 個整數計數（`structural_pass`、`semantic_pass`、`both_pass`、`structural_only`、`semantic_only`、`both_fail`）；實作輸出寫入與 summary 聚合計算讓測試通過
- [x] 3.2 為「Async execution with caching for cost control」要求與 design 的「Async 並行：max_concurrent=10」決定寫測試：呼叫 `evaluate()` 時 kwargs 含 `AsyncConfig(run_async=True, max_concurrent=10)` 與 `CacheConfig(use_cache=True, write_cache=True)`；實作 config 傳遞讓測試通過
- [x] 3.3 寫 CLI 測試：`python -m evals.deepeval_judge --model gemini-vertex` 讀對檔案、寫對輸出路徑、unknown model 退出非 0；實作 typer CLI 入口讓測試通過

## 4. 跑 semantic judge 產出 results-deepeval

- [x] 4.1 [P] 對 `gemini-vertex` 跑 `python -m evals.deepeval_judge --model gemini-vertex`（驗證「Semantic judge layer evaluates stored responses without re-calling APIs」端到端正確）產出 `evals/results-deepeval/gemini-vertex.json`，並用該檔人工抽 3 個 `judge_disagreement=true` 的 query 確認 judge 結果合理
- [x] 4.2 [P] 對 `gemma4` 跑 `python -m evals.deepeval_judge --model gemma4` 產出 `evals/results-deepeval/gemma4.json`，同樣抽查 disagreement 的 query
- [x] 4.3 [P] 對 `gpt51` 跑 `python -m evals.deepeval_judge --model gpt51` 產出 `evals/results-deepeval/gpt51.json`，同樣抽查 disagreement 的 query

## 5. Synthesizer 探索與產出

- [x] 5.1 為「Synthesizer exploration generates queries from scratch」要求與 design 的「Synthesizer 探索範圍」決定，寫 `evals/synthesizer_explore.py`：呼叫 `Synthesizer.generate_goldens_from_scratch` 帶 subject="GitHub natural language query about open-source repos, releases, issues, contributors"、task="answer technical questions by searching GitHub"、`evolution_types=["REASONING", "COMPARATIVE", "MULTICONTEXT"]`、`max_goldens=15`
- [x] 5.2 為「Generated output is preserved for offline review」要求實作輸出寫到 `evals/synthesized-queries/<ISO-timestamp>.json`（每筆含 `input`、`expected_output`、`evolution_type`），跑一次產出實際檔案，確認檔案存在且至少含 12 筆

## 6. Findings document compares synthesized queries against manual set

- [x] 6.1 為「Findings document compares synthesized queries against manual set」要求手動 review 產出的 synthesized queries，寫 `evals/synthesized-queries/findings.md`：四段分別評估（1）GitHub scope 符合度、（2）多語言覆蓋、（3）eval-leakage 風險、（4）是否能直接補進 production validation set；每段至少引用 2 個具體 query 例子作為佐證

## 7. 文件更新

- [x] 7.1 更新 `evals/README.md` 加 `Semantic Judge Layer` 章節：說明 `deepeval_judge.py` 用法、4 個 metric 含義、threshold 值、judge model 預設與覆寫方式、輸出 schema（即 design 的「結果儲存：`evals/results-deepeval/{model}.json`」schema）
- [x] 7.2 更新 `README.md` 在 `Eval Design Learnings` 後加新章節「跨 judge 對照」：列出三個 model 的 structural / semantic 分數對照表、`structural_pass 但 semantic_fail` 的代表題例子、Synthesizer 探索結果摘要（呼應 findings.md）
