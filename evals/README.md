# ghibli Eval Pipeline

多模型評測框架，測試不同 LLM 把自然語言查詢轉成正確 GitHub Function Calling 結構化輸出的能力。

## 檔案結構

```
evals/
├── queries.yaml                # 30 題查詢 + ground truth
├── models.py                   # LiteLLM 多後端包裝 + model registry
├── run_evals.py                # Runner（逐題執行，寫入 per-model 結果檔）
├── judge.py                    # Multiset 判分 + refuse scenario 判分
├── compare_models.py           # 從 per-model 結果產 Markdown 比較表
├── rejudge.py                  # 不重跑 API，用 stored result 套新 judge / 新 GT 快速重判
├── deepeval_judge.py           # 語意級 judge（LLM-as-judge，4 個 metric）
├── synthesizer_explore.py      # 一次性實驗：Synthesizer 自動生題對照
├── tool_schema.py              # Re-export ghibli 的 tool schemas
├── results/                    # 結構級判分結果（每 model 一檔）
│   ├── gemini-vertex.json
│   ├── gemma4.json
│   └── gpt51.json
├── results-deepeval/           # 語意級判分結果（每 model 一檔）
│   ├── gemini-vertex.json
│   ├── gemma4.json
│   └── gpt51.json
└── synthesized-queries/        # Synthesizer 產出 + findings（JSON gitignored）
    └── findings.md
```

## Query Schema（`queries.yaml`）

30 題 × **6 個 scenario category**（每類 5 題）。Category 是「使用者在做什麼」，不是「哪種失敗模式」——失敗模式是另一個正交的 tag 維度。

| Scenario | 意義 |
|---|---|
| `discover` | 發掘陌生工具/repo（沒有明確目標，靠搜尋找候選） |
| `compare` | 對比兩個以上選項 |
| `debug_hunt` | 找類似 bug / issue —「我遇到某錯誤，有人遇過嗎？」 |
| `track_vuln` | 安全事件 / 版本追蹤 |
| `follow_up` | 對已知 repo 深挖（contributors / releases / commits / README / 語言分佈） |
| `refuse` | 模型應識別為不可行並拒絕呼叫工具（可混合正常 + 矛盾子問題） |

### 每題欄位

```yaml
- id: <scenario>-NNN
  category: <scenario>
  failure_modes: [tag, tag, ...]    # 多標籤（可 0–N 個），跟 category 正交
  query: "<自然語言查詢>"
  query_language: ko                # 非中/非英時必填
  query_meaning: |                  # query_language 有值時必填
    中文: ...
    English: ...
  expected_behavior: "<英文精簡描述>"
  difficulty: easy | medium | hard
  notes: |
    <背景、issue 連結、工具呼叫推理>
  ground_truth:
    tool: <tool_name | "refuse">
    params: { q_contains: "...", owner: "...", repo: "..." }
    tool_sequence: [tool_a, tool_b, ...]
    # refuse 專用：
    valid_parts_tool_sequence: [...]
    refusal_keywords: [...]
```

### Failure mode tags（7 個）

分兩組：

**輸入形態類**（使用者 query 怎樣難）：
- `multilingual`：語言本身是 stressor（非中英、或非中英混雜）
- `ambiguous_input`：資訊不完整或印象模糊
- `messy_phrasing`：口語 / 俚語 / 低標點 / run-on
- `outdated_assumption`：使用者預設錯誤事實，測模型會不會 push back
- `typo`：打錯 package / model / repo 名

**機制類**（模型要做什麼）：
- `qualifier_mapping`：自然語言 → GitHub API qualifier（license:mit SPDX 等）
- `temporal_reasoning`：時間語意推理、日期換算

### 多語言覆蓋

PDF Part 1 要求 "languages other than English"。每個 category 配一種非中英語言：

| Category | 語言 |
|---|---|
| `discover-004` | 한국어（韓文）|
| `compare-003` | Deutsch（德文）|
| `debug_hunt-001` | Tiếng Việt（越南文）|
| `track_vuln-002` | 日本語 |
| `follow_up-003` | ภาษาไทย（泰文）|
| `refuse-004` | Español（西文）|

## Judge 邏輯（`judge.py`）

```python
judge(tools_called, response_text, ground_truth) -> dict
```

回傳 `{ tool_match, sequence_match, flagged_refusal (refuse only), pass_ }`。

### 一般 scenario

- **`tool_match`**：`ground_truth.tool` 必須出現在 `tools_called` 裡（set membership）
- **`sequence_match`**：**multiset subset** ——`tool_sequence` 裡每個工具都要在 `tools_called` 出現**至少那麼多次**。**順序不管**。
  - 理由：data dependency 自然強制順序（search 必在 get_repository 前因為後者需前者 owner/repo）。硬性 sequence 檢查是 artificial discipline。
- **`pass_ = tool_match AND sequence_match`**

### Refuse scenario（`tool: refuse`）

Refuse 類 query 混合兩種子問題在同一題裡——**可回答的部分**（例如「找出活躍的 Rust web framework」）跟**邏輯上不可行的部分**（例如「其中 fork 數超過 star 數的」，這在 GitHub 上幾乎不成立）。測的是模型能不能同時：
1. 正常部分呼叫對的工具去查答案
2. 不可行的部分**明確拒絕**，而不是幻想出結果

Ground truth 用兩個 key 表達這個期望：
- `valid_parts_tool_sequence`：要答正常部分**必須**呼叫的工具（判 `sequence_match`，multiset）
- `refusal_keywords`：回應裡必須包含的拒絕性詞彙（例如「無法」、「不可能」、「inherently contradictory」——判 `flagged_refusal`，case-insensitive）

- **`pass_ = sequence_match AND flagged_refusal`**——兩個條件都要達成（有呼叫工具查正常部分 **且** 明確拒絕不可行部分）

## Runner（`run_evals.py`）

```bash
uv run python -m evals.run_evals --model <name>
uv run python -m evals.run_evals --model <name> --category <scenario>

# 針對特定 query ID 跑（調 harness 後針對失敗題重跑不重算整組）
uv run python -m evals.run_evals --model <name> --query-ids 'compare-002,debug_hunt-003'
```

可用的 model 名稱寫在 `_VALID_MODELS`（對應 `models.py` 的 `_MODEL_CONFIG`）。
`--query-ids` 傳多個 ID 用逗號分隔，會覆蓋 `--category`。

每次執行會：
1. 載入 `queries.yaml`
2. 對每題：呼叫 `chat_with_model(query, session_id, model_name)`——透過 LiteLLM 帶 13 個 tool schema 實際對 GitHub API 執行工具
3. 即時輸出 `→ tool(args)` 跟 `← result preview`（像 CLI 一樣看到過程）
4. 跑 `judge(tools_called, response_text, ground_truth)`
5. 把 `run_obj` append 到 `evals/results/{model}.json`

每題結果包含：
- `tools_called`：工具名稱有序 list（給 judge 用）
- `tool_calls_detail`：完整 `[{tool, args, result_preview}, ...]`——可驗證答案是否 grounded in actual tool output
- `response_full`：模型完整回應
- `duration_seconds`、`status`（pass/fail/error）、`error_message`
- `judge_result`：`{ tool_match, sequence_match, flagged_refusal, pass_ }`

**重要語意**：
- `status: "pass"` = execution 成功（沒有 crash）
- `judge_result.pass_` = 真的答對（用於算 accuracy）
- 兩個 pass 不同意思！accuracy 看後者。

## Model Registry（`models.py`）

`_MODEL_CONFIG` 映射 short nickname → `{ model_id, api_key_env | vertex_project_env, extra_body, ... }`。

**最終 3 個模型**：

| Nickname | 模型 | Provider |
|---|---|---|
| `gemini-vertex` | `gemini-3-flash-preview` | Vertex AI（ADC，global endpoint） |
| `gemma4` | `gemma-4-26b-a4b-it` | Gemini API（open-weight） |
| `gpt51` | `gpt-5.1-2025-11-13` | OpenAI |

**Gemini 2.5 Flash → Gemini 3 Flash 的切換**：原本 `gemini-vertex` 配的是 `gemini-2.5-flash`，迭代過程中換成 `gemini-3-flash-preview`。2.5 Flash 在最佳狀態下只能到 ~77%，上限明顯；3 Flash 有 thinking 能力、tool planning 更穩定，最後能達到 96.7%。

### 每個 model 的 config 欄位

`_MODEL_CONFIG` 支援以下欄位（每個模型按需設）：

- `model_id`：LiteLLM model 路徑
- `api_key_env` / `vertex_project_env`：環境變數名
- `vertex_location`：Vertex region（preview model 必須 `"global"`）
- `reasoning_effort`：`none` / `low` / `medium` / `high`（OpenAI / Vertex Gemini 3+ 支援）

### Retry 策略

- `RateLimitError`（429）：解析 "try again in Xs" → sleep + retry
- `ServiceUnavailableError`（503）/ `Timeout` / `ConnectionError`：exponential backoff（5s, 10s, 20s, 40s, 80s），最多 5 次後 raise

## 比較報表（`compare_models.py`）

```bash
uv run python -m evals.compare_models
```

從 `evals/results/*.json`（不讀 archive）抓每個模型最新 run，輸出 Markdown accuracy 表：

```
| Model | Overall | Discover | Compare | Debug Hunt | Track Vuln | Follow Up | Refuse |
| ----- | ------- | -------- | ------- | ---------- | ---------- | --------- | ------ |
| ...
```

## Rejudge 工具（`rejudge.py`）

```bash
uv run python -m evals.rejudge              # 所有模型
uv run python -m evals.rejudge --model gpt51
uv run python -m evals.rejudge --detail     # 顯示失敗 query 細節
```

**用途**：改了 `judge.py` 或 `queries.yaml` 的 ground truth，不想重跑 API（燒錢 + 耗時）時——讀 stored `tools_called` + `response_full`，用**當前的**judge.py + queries.yaml 重判分。秒級完成。

這是 eval design 的關鍵 enabler：快速 iterate GT 跟 judge 邏輯，不被 API 成本綁住。

## Semantic Judge Layer（`deepeval_judge.py`）

結構級判分（multiset subset）只查「該 call 的工具有沒有 call」，不查「答案到底對不對」。Semantic judge 是疊在上面的第二層判分，用 LLM-as-judge 看 stored response 的內容品質，補結構級的盲點。

### 用法

```bash
uv run python -m evals.deepeval_judge --model gemini-vertex
uv run python -m evals.deepeval_judge --model gemma4
uv run python -m evals.deepeval_judge --model gpt51
```

讀 `evals/results/{model}.json` 的 stored response 跟 tool_calls_detail，跑 4 個 metric，輸出到 `evals/results-deepeval/{model}.json`。**不重打 GitHub API、不重打 under-test model**——成本只在 judge LLM 端。

如果遇到 timeout（少數 query 的 judge 回應過慢），加 env var：

```bash
DEEPEVAL_PER_ATTEMPT_TIMEOUT_SECONDS_OVERRIDE=300 uv run python -m evals.deepeval_judge --model <name>
```

### 4 個 Metric

| Metric | 在判什麼 | Threshold |
|---|---|---|
| `AnswerRelevancyMetric` | 答案有沒有真的回到使用者問的問題 | 0.7 |
| `FaithfulnessMetric` | 答案是不是 grounded 在 tool 拿到的資料 | 0.7 |
| `HallucinationMetric` | 模型有沒有編造 GitHub 上不存在的 repo / 數字 / 版本 | 0.7 |
| `GEval("Partial Refusal Quality")` | refuse 類專用——valid 部分有沒有正常答 + 矛盾部分有沒有明確拒絕 | 0.6 |

非 refuse 類 query 的 `partial_refusal` 記錄為 null，reason `"N/A non-refuse"`。

`HallucinationMetric` 收的 `context` 不是 judge LLM 的訓練知識，而是 stored `tool_calls_detail` 的 `result_preview`——這樣 judge 是「模型答的東西在不在 tool 結果裡」，不是「judge 自己記不記得這個 repo」。

### Judge Model

預設 `gemini/gemini-2.5-flash`（透過 `GEMINI_API_KEY`）。透過 env var 覆寫：

```bash
DEEPEVAL_JUDGE_MODEL=openai/gpt-4o uv run python -m evals.deepeval_judge --model gemma4
```

**為什麼選 Gemini 2.5 Flash 不選 Anthropic / GPT**：ghibli 沒設 `ANTHROPIC_API_KEY`、`gpt-4o` 跟 `gpt51` 同 provider 有同源偏見；Gemini 2.5 Flash 跟 3 個 under-test model 的版本 / provider / endpoint 都不同（gemini-vertex 跑 3 Flash via Vertex、gemma4 是 open-weight Gemma、gpt51 是 OpenAI），bias 風險可控。

**已知 caveat**：Gemini judge 會被 safety filter 影響，遇到 CVE / vulnerability 內容偶爾回傳 None，判分會被記成 `judge returned no score` 並從 semantic_pass 計算中跳過（不會炸整個 run，因為已開 `ignore_errors=True`）。

### 輸出 schema

```json
{
  "judge_model": "gemini/gemini-2.5-flash",
  "model": "gemini-vertex",
  "results": [
    {
      "query_id": "track_vuln-001",
      "structural_pass": true,
      "metrics": {
        "answer_relevancy": {"score": 0.85, "passed": true, "reason": "..."},
        "faithfulness":     {"score": 0.92, "passed": true, "reason": "..."},
        "hallucination":    {"score": 0.15, "passed": true, "reason": "..."},
        "partial_refusal":  {"score": null, "passed": null, "reason": "N/A non-refuse"}
      },
      "semantic_pass": true,
      "judge_disagreement": false
    }
  ],
  "summary": {
    "structural_pass": 29,
    "semantic_pass":   29,
    "both_pass":       28,
    "structural_only":  1,
    "semantic_only":    1,
    "both_fail":        0
  }
}
```

`judge_disagreement` 是核心 signal——`structural_pass != semantic_pass` 的 query 才是現有 eval 的真正盲點。

### Async 與快取

預設帶 `AsyncConfig(run_async=True, max_concurrent=10)` 跟 `CacheConfig(use_cache=True, write_cache=True)`：

- 30 題 × 3-4 metric ≈ 90-120 judge call，max_concurrent=10 約 2-5 分鐘跑完
- 重跑相同 stored response 直接吃 cache（在 `~/.deepeval/.deepeval-cache.json`），秒級完成

## Synthesizer 探索（`synthesizer_explore.py`）

一次性實驗：用 DeepEval `Synthesizer.generate_goldens_from_scratch` 自動生 15 條 query，跟手動 30 題對比 diversity / scope / 適用度。

```bash
uv run python evals/synthesizer_explore.py
```

輸出到 `evals/synthesized-queries/<ISO-timestamp>.json`（gitignored），review 結論寫在 `evals/synthesized-queries/findings.md`。**生成的題不進 production validation set**——四個維度評估後不適用，理由見 findings 檔。

## Ground-Truth 設計原則

1. **多步優先**：非 refuse 類 query 如果一個工具答不出預期答案，`tool_sequence` 就要 ≥ 2 個。
2. **單工具足夠也 OK**：例如 `search_issues q='repo:owner/name keyword'` 本身就 scope 到特定 repo——強求前置 `get_repository` 只是紀律檢查，不是必要。所以 debug_hunt / track_vuln 有些題目 `tool_sequence: [search_issues]` 單工具。
3. **Multiset，非 subsequence**：順序不管，計數要對。
4. **Refuse 測 partial refusal**：正常部分必須 call 工具，不可行部分必須**在回應中明確拒絕**（關鍵字比對）。
5. **Prompt 無 eval leakage**：具體 ground truth 細節（repo 名、impossibility 門檻）禁止出現在 `src/ghibli/prompt.py`。

### Ground-Truth audit 原則（重要）

`list_*` / `get_readme` / `get_languages` 系列工具**直接吃 `owner + repo` 作 input**，不需要前置 `get_repository` 當 anchor。所以 GT 把這類「紀律性 anchor」移掉，只要求**功能上必要**的工具。

具體適用：debug_hunt（5 題）、track_vuln（部分）、follow_up（部分）的 `tool_sequence` 都已移除 redundant `get_repository`。

保留 `get_repository × N` 嚴格要求的場景：compare N-way（要 N 個 repo 各自 metadata），follow_up deep-dive（repo metadata 作 anchor）。

## Content Validation 的考量（試過但撤回）

曾經在 `judge.py` 加 `required_content_all` / `required_content_any_of` 檢查回應內容關鍵字，但撤回了。理由：

1. **Keyword matching 脆弱**：模型用多國語言、同義詞、不同表達都可能被 false negative
2. **冗餘**：模型若 call 對工具拿真實 data，回應自然會 mention 相關 keyword——tool_sequence 驗證已足夠
3. **測錯東西**：content validation 容易變成「測 keyword 模式」而非測「grounding + 答題能力」

目前 refuse 仍保留 `refusal_keywords` 機制——因為那測的是**明確拒絕語意**，不是內容關鍵字比對。
