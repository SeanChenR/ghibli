## Why

Assessment Part 2 要求對自然語言 → GitHub API 的轉換品質做多模型評測：手動標注 30 條 ground truth、用至少 3 個不同來源的模型跑 eval pipeline、迭代 prompt 直到所有模型準確率超過 85%，並在 README 寫出分析報告。目前 ghibli 只用 Gemini 2.5 Flash，沒有 ground truth 標注、沒有準確率量測機制、也沒有跨模型比較能力。

## What Changes

- 為 `evals/queries.yaml` 的每條 query 加入 `ground_truth` 欄位，標注正確應呼叫的 tool 名稱與關鍵參數
- 新增 `evals/judge.py`：比對模型實際呼叫的 tool/params 與 ground truth，輸出 pass/fail 與 accuracy
- 新增 `evals/models.py`：LiteLLM 統一介面，支援 Gemini 2.5 Flash（閉源）、GPT-4o-mini（閉源）、Llama 3.3 via Groq（開源）
- 修改 `evals/run_evals.py`：支援 `--model` 參數切換模型，結果記錄每個模型的 accuracy
- 新增 `evals/compare_models.py`：讀取 results.json，跨模型比較 accuracy 並輸出 Markdown 表格
- 更新 README：加入 Part 2 write-up（模型選擇理由、效能比較、eval 設計心得）

## Non-Goals

- 不實作自動 prompt 最佳化（人工迭代 system prompt 直到 >85%）
- 不支援 streaming 輸出的模型評測
- 不把 LiteLLM 引入主要 CLI 流程，只用於 eval pipeline

## Capabilities

### New Capabilities

- `ground-truth-catalog`: 30 條 query 的手動 ground truth 標注，作為 eval 評分依據
- `multi-model-runner`: LiteLLM 多模型 eval runner，支援閉源與開源模型
- `eval-judge`: 結構化比對 tool call 與 ground truth，計算 per-query pass/fail 與整體 accuracy

### Modified Capabilities

- `eval-harness`: 新增 ground_truth 欄位到 queries.yaml schema；results.json 新增 accuracy 與 model 欄位

## Impact

- Affected specs: `ground-truth-catalog`（新增）、`multi-model-runner`（新增）、`eval-judge`（新增）、`eval-harness`（修改）
- Affected code:
  - `evals/queries.yaml` — 加入 ground_truth 欄位
  - `evals/run_evals.py` — 加入 --model 參數與 accuracy 計算
  - `evals/judge.py` — 新增
  - `evals/models.py` — 新增
  - `evals/compare_models.py` — 新增
  - `pyproject.toml` — 加入 litellm dependency
  - `README.md` — Part 2 write-up
