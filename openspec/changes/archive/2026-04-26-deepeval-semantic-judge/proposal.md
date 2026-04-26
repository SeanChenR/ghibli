## Why

目前的 eval pipeline 只判「該呼叫的工具有沒有呼叫」，沒判「最後給的答案是真是假」。三個失分盲點：

1. 模型呼叫對所有工具但**捏造一個不存在的 repo 名**——目前判 PASS
2. 模型呼叫對所有工具但**完全沒回到使用者問的點**——目前判 PASS
3. 模型呼叫對所有工具但**數字 / 日期 / 版本寫錯**——目前判 PASS

README 已經承認這個盲點（仍無法根解的限制 §5：Judge 是結構級、非語義級），但只是承認沒補。這次補上：用 DeepEval 跑語意級的第二層判分，疊在現有結構級判分之上。**不取代現有 pipeline**，是 additive 的第二維度。

順便試 DeepEval 的 Synthesizer 自動生題，看看 LLM-generated query 跟手動 + Claude Code co-design 出來的 30 題比起來品質如何，當作 validation set 設計的對照組探索。

## What Changes

新增**語意級判分層**（讀 stored response 重新判分，不重打 GitHub API）：

- 4 個 metric per query：`AnswerRelevancyMetric` / `FaithfulnessMetric` / `HallucinationMetric` / `GEval("Partial Refusal Quality")`
- 每個 model 跑 30 題 × 4 metric = 120 個 judge call
- 寫入 `evals/results-deepeval/{model}.json`
- 產出跨 judge 比較報表：「結構級 PASS 但語意級 FAIL」的題目清單，這才是現有 eval 的真正盲點

新增 **Synthesizer 探索**（一次性實驗，看 LLM 自動生題長什麼樣）：

- 用 `Synthesizer.generate_goldens_from_scratch` 設定 subject = "GitHub natural language query"
- 跑 3 種 evolution type（REASONING / COMPARATIVE / MULTICONTEXT）各生 5 題
- 輸出到 `evals/synthesized-queries/<timestamp>.json`
- 寫 findings 報告：跟手動 30 題比品質 / 多樣性 / eval leakage 風險

新增 README 章節：在現有 eval write-up 加「語意級判分對照」+「Synthesizer 探索結果」兩段。

## Non-Goals

- **不取代現有結構級 judge**：multiset subset + refusal keywords 仍是主要判分，DeepEval 是補語意層
- **不接 Confident AI cloud**：本地跑、本地存，不上傳資料
- **不整合進 pytest CI**：DeepEval judge 跑一次要打數百個 LLM API call，CI 跑成本太高，留作手動執行
- **Synthesizer 生出來的題不進 production validation set**：只做探索，30 題仍是手動 curated
- **不評估多輪對話 / 多模態 metric**：ghibli 是單輪文字 Q&A，這些 metric 不適用
- **不重跑 GitHub API**：rejudge 模式從 stored `response_full` + `tool_calls_detail` 判分，避免重複 API 成本

## Capabilities

### New Capabilities

- `semantic-judge`：語意級判分層，用 LLM-as-judge 評估 stored response 的答案品質（relevancy / faithfulness / hallucination / refusal quality）
- `query-synthesizer-exploration`：Synthesizer 自動生題的一次性探索與產出比較報告

### Modified Capabilities

(none)

## Impact

- Affected specs：新增 `semantic-judge` 與 `query-synthesizer-exploration` 兩個 capability
- Affected code:
  - New: `evals/deepeval_judge.py`、`evals/synthesizer_explore.py`、`evals/results-deepeval/gemini-vertex.json`、`evals/results-deepeval/gemma4.json`、`evals/results-deepeval/gpt51.json`、`evals/synthesized-queries/findings.md`、`tests/unit/test_deepeval_judge.py`
  - Modified: `pyproject.toml`（加 `deepeval` 依賴）、`evals/README.md`（pipeline reference 加 semantic judge 章節）、`README.md`（write-up 加跨 judge 對照 + synthesizer 探索結果）、`.gitignore`（synthesized-queries 中間產物排除規則）
  - Removed: (none)
