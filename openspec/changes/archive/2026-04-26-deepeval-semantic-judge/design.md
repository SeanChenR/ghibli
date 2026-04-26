## Context

ghibli 目前的 eval pipeline（`evals/run_evals.py` + `evals/judge.py` + `evals/results/`）是純結構級判分：multiset subset 比對 tool 序列、refusal keyword check。30 題 × 3 model 已達成 ≥85% threshold（86.7 / 90 / 96.7），但 README 已點明這個分數**不能保證答案內容正確**，只能保證選對工具。

外部現況：DeepEval 是 pytest 風格 LLM eval 框架，提供 50+ metric。對 ghibli 這種「NL → 結構化 GitHub query」場景，相關的是 RAG + Agent metric（answer relevancy / faithfulness / hallucination）以及 G-Eval 自訂 LLM judge。Synthesizer 是另一個 feature，能用 LLM 自動從 subject 生成 query。

約束：
- 不能重新打 GitHub API（已存的 `evals/results/{model}.json` 含 response_full + tool_calls_detail 足夠 rejudge）
- 不破壞現有結構級判分流程（`evals/run_evals.py` / `judge.py` / `compare_models.py` 都不動）
- LLM judge 會花錢，需要可關 cache、可控並行
- Synthesizer 探索是一次性實驗，不是 production 機制

## Goals / Non-Goals

**Goals**：
- 用 DeepEval 在 stored response 上跑 4 個語意 metric，產出第二維度的判分
- 找出「結構級 PASS 但語意級 FAIL」的題目作為現有 eval 盲點的證據
- 跑一次 Synthesizer 探索，記錄 LLM 自動生題的品質特徵
- 在 README write-up 補一段「跨 judge 對照」+「Synthesizer 探索結果」

**Non-Goals**（呼應 proposal）：
- 不做 multiturn / 多模態 metric
- 不接 Confident AI cloud
- 不整合進 CI（手動執行）
- Synthesizer 產出的題不進 production validation set

## Decisions

### LLM judge 模型用 Gemini 2.5 Flash

DeepEval 官方推薦 Anthropic Claude，但 ghibli 沒有 ANTHROPIC_API_KEY，只有 GEMINI_API_KEY / OPENAI_API_KEY / GOOGLE_CLOUD_PROJECT。Judge 用 **Gemini 2.5 Flash（透過 GEMINI_API_KEY 路徑、LiteLLM `gemini/gemini-2.5-flash`）**，理由：

- credential 已備好，不需新加 env var
- 跟現有 3 個 under-test model 的版本 / provider / endpoint 都不同：`gemini-vertex` 跑 Gemini 3 Flash via Vertex AI、`gemma4` 是開源 Gemma-4-26b、`gpt51` 是 OpenAI——降低 self-judging bias
- DeepEval 內建支援 LiteLLM model id，整合簡單

替代方案：
- **Anthropic Claude**：要新加 ANTHROPIC_API_KEY、安裝 anthropic SDK，效益不顯著
- **OpenAI gpt-4o**：跟 gpt51 同 provider 同公司有同源偏見
- **不用 LLM judge，用 deterministic scorer（ROUGE/BLEU）**：對 ghibli 中文混雜場景效果差

**Bias 評估**：

| 被判 model | 跟 judge（Gemini 2.5 Flash）的關係 | 同源偏見風險 |
|---|---|---|
| `gemini-vertex`（Gemini 3 Flash via Vertex）| 同 family 不同版本 + 不同 endpoint（API Key vs Vertex） | 中等 |
| `gemma4`（Gemma-4-26b open-weight）| 同公司（Google）但不同產品線（Gemma 開源 vs Gemini 閉源） | 中等偏低 |
| `gpt51`（GPT-5.1） | 不同 family 不同公司 | 低 |

接受 gemini-vertex 與 gemma4 的中等同源風險，在 cross-judge 比較報表標註此 caveat。透過 env var `DEEPEVAL_JUDGE_MODEL` 可覆寫成其他 model 做後續驗證。

### DeepEval 跑 rejudge 模式（讀 stored response，不重打 API）

`deepeval_judge.py` 的工作流：

```
讀 evals/results/{model}.json → 對每筆 result：
  ├─ 抽 input (query)、actual_output (response_full)、tool_calls_detail
  ├─ 從 tool_calls_detail 提 result_preview 當 retrieval_context
  └─ 跑 4 個 metric → 寫進 evals/results-deepeval/{model}.json
```

替代方案：
- **重新跑 30 題再判**：成本 × 2，且模型輸出有隨機性，無法跟現有結構級分數對齊比較
- **跟 run_evals.py 整合成同一個 runner**：耦合太多，後續調整 deepeval 部分會影響主 pipeline；保持兩個獨立 script 比較乾淨

### 4 個 metric 的選擇

| Metric | 為什麼選 | 為什麼不選別的 |
|---|---|---|
| `AnswerRelevancyMetric` | 答案有沒有回到問題 | `ConversationCompleteness` 是多輪用的 |
| `FaithfulnessMetric` | 答案是否 grounded 在 tool 結果 | `ContextualRecall` 需要 expected_output 對齊 retrieval，我們沒這欄 |
| `HallucinationMetric` | 抓編造 repo 名 / 數字 / 版本 | 直接相關，沒有更好替代 |
| `GEval("Partial Refusal Quality")` | refuse 類用 keyword 比對太脆弱，G-Eval 能判「拒絕得合不合理」 | `BiasMetric` / `ToxicityMetric` 不適用 |

threshold 設定：
- AnswerRelevancy / Faithfulness / Hallucination：`0.7`（DeepEval 預設保守值）
- GEval Partial Refusal：`0.6`（比較主觀的判斷給寬一點）

### 結果儲存：`evals/results-deepeval/{model}.json`

Schema：
```json
{
  "judge_model": "gemini/gemini-2.5-flash",
  "results": [
    {
      "query_id": "track_vuln-001",
      "structural_pass": true,
      "metrics": {
        "answer_relevancy": {"score": 0.85, "passed": true, "reason": "..."},
        "faithfulness": {"score": 0.92, "passed": true, "reason": "..."},
        "hallucination": {"score": 0.15, "passed": true, "reason": "..."},
        "partial_refusal": {"score": null, "passed": null, "reason": "N/A non-refuse"}
      },
      "semantic_pass": true,
      "judge_disagreement": false
    }
  ],
  "summary": {
    "structural_pass": 26,
    "semantic_pass": 24,
    "both_pass": 22,
    "structural_only": 4,
    "semantic_only": 2,
    "both_fail": 2
  }
}
```

`partial_refusal` metric 只對 `refuse` 類 5 題跑，其他 25 題寫 null。`judge_disagreement = structural_pass != semantic_pass`，這是 cross-judge 比較表的核心 signal。

### Synthesizer 探索範圍

跑 `Synthesizer.generate_goldens_from_scratch`（不是 from_docs，因為 ghibli 沒文件庫），參數：
- `subject = "GitHub natural language query about open-source repos, releases, issues, contributors"`
- `task = "answer technical questions by searching GitHub"`
- `evolution_types = ["REASONING", "COMPARATIVE", "MULTICONTEXT"]`（每種 5 題，共 15 題）
- `max_goldens = 15`

輸出 `evals/synthesized-queries/<timestamp>.json` + 一份 `evals/synthesized-queries/findings.md` 記錄：
1. LLM 生出來的題是否符合 ghibli scope（限 GitHub 領域）
2. 多語言覆蓋如何（手動 30 題有 6 種非英語，LLM 生的呢）
3. 是否有 eval leakage 風險（LLM 生 query 又生 GT，模型自己跟自己對答案）
4. 是否能直接補進 production validation set（誠實判斷）

### Async 並行：max_concurrent=10

DeepEval 支援 `AsyncConfig(max_concurrent=N)`。30 題 × 4 metric = 120 個 judge call，max_concurrent=10 預估 2-3 分鐘跑完一個 model。Cache 開啟（`CacheConfig(use_cache=True, write_cache=True)`），重跑同樣的 stored response 不會重新打 API。

替代方案：
- max_concurrent=20（DeepEval 預設）：擔心 OpenAI rate limit 觸發 retry
- max_concurrent=5：太慢

## Risks / Trade-offs

| Risk | Mitigation |
|---|---|
| LLM judge 非 deterministic，同題兩次跑分數可能不同 | DeepEval 內建 cache 打開；報表標明「judge 結果為單次跑分，會有 ~5-10% 變動」 |
| Judge model 自己會幻想：說某 repo 不存在但其實存在 | 用 retrieval_context（從 tool_calls_detail 來）作 ground truth，要求 judge 只能基於該 context 判分 |
| Synthesizer 生出的題太發散，跟 ghibli scope（GitHub）無關 | 在 subject 寫死 GitHub 限制；產出 review 時手動標註 in-scope / out-of-scope |
| Gemini 2.5 Flash judge 跟 `gemini-vertex` / `gemma4` 同公司，有中等同源偏見 | 在 cross-judge 比較表標註此 caveat；env var `DEEPEVAL_JUDGE_MODEL` 可覆寫成其他 model 做後續驗證 |
| DeepEval 安裝後 dependency 衝突（litellm 版本等） | 用 `uv add deepeval` 跑 lock，遇到衝突再評估降版或排除 |
| `evals/results-deepeval/*.json` 體積大（每題含 metric reason） | 結構控制在合理範圍；若超過 1MB/file 考慮分檔 |

## Migration Plan

1. `uv add deepeval` 加依賴，跑 lock
2. 寫 `evals/deepeval_judge.py`（rejudge mode）
3. 對 3 個 model 各跑一次，產出 `evals/results-deepeval/{model}.json`
4. 寫 `evals/synthesizer_explore.py` + 跑一次，產出 `evals/synthesized-queries/findings.md`
5. 更新 `evals/README.md`：加 semantic judge 章節（pipeline reference）
6. 更新 `README.md`：在 Eval Design Learnings 加跨 judge 對照表 + synthesizer findings 摘要

無 rollback 需求——新加的檔案不影響既有結構級判分；隨時可以 `git revert` 拿掉這個 commit。

## Open Questions

無未決問題。所有決策（judge model 選擇、threshold、metric 數量、async 並行度、Synthesizer 範圍）都已在上方明確。
