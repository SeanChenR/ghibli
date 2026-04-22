## Context

ghibli 已有 30 條 eval query（`evals/queries.yaml`）、runner（`evals/run_evals.py`）、以及 Gemini 2.5 Flash 的 tool-calling agent。現行 eval 的 pass/fail 判斷是「只要有回覆就算 pass」，不驗證模型是否呼叫了正確的 tool 或帶了正確的參數，因此無法量測「準確率」。

Part 2 需要：
1. 手動標注 ground truth（正確 tool + 關鍵參數）
2. 切換不同模型跑 eval
3. 比對輸出與 ground truth 計算 accuracy
4. 迭代 system prompt 直到 3 個模型都 >85%

## Goals / Non-Goals

**Goals:**

- 為所有 30 條 query 標注 ground truth（tool 名稱 + 關鍵參數）
- 新增 LiteLLM 介面，支援 Gemini 2.5 Flash、GPT-4o-mini、Llama 3.3（Groq）
- 新增 judge 模組，比對 tools_called 與 ground truth，計算 accuracy
- run_evals.py 支援 `--model` 切換，results.json 新增 model 與 accuracy 欄位
- 新增 compare_models.py 輸出跨模型比較表格

**Non-Goals:**

- 不改變主要 CLI 的 LLM 呼叫邏輯（仍使用 google-genai SDK）
- 不自動最佳化 prompt（人工迭代）
- 不支援 Vertex AI 模式下的多模型切換

## Decisions

### Ground Truth 標注格式

ground truth 直接加在 `evals/queries.yaml` 每條 entry 的 `ground_truth` 欄位，不另開獨立檔案。

理由：保持 query 定義與期望答案在同一位置，judge 讀取時不需要 join 兩個資料來源，且 YAML 格式易於人工編輯。

格式定義：
```yaml
ground_truth:
  tool: search_repositories          # 必填：期望呼叫的 tool 名稱（單一或最後一個）
  params:                            # 必填：關鍵參數的 partial match 條件
    q_contains: "python"             # q 參數需包含此字串（用於 search_repositories）
    owner: "facebook"                # 精確 match（用於 list_issues 等）
    repo: "react"
  tool_sequence: [search_repositories, list_releases]  # 可選：multi-step 查詢的 tool 呼叫順序
```

判斷邏輯（`judge.py`）：
- `tools_called` 包含 `ground_truth.tool` → tool match ✓
- 若有 `tool_sequence`，`tools_called` 需依序包含所有 tool → sequence match ✓
- `params` 為 partial match：只驗證有標注的欄位，不要求完全吻合
- 三項全符合 → pass；任一不符 → fail

### LiteLLM 多模型介面

新增 `evals/models.py`，封裝 LiteLLM 呼叫，提供與 `agent.chat()` 相同簽名的函式 `chat_with_model(user_message, session_id, model_name)`。

模型對應表：
| model_name | LiteLLM 模型 ID | 類型 |
|---|---|---|
| `gemini` | `gemini/gemini-2.5-flash` | 閉源 |
| `gpt4o-mini` | `openai/gpt-4o-mini` | 閉源 |
| `llama3` | `groq/llama-3.3-70b-versatile` | 開源（via Groq API） |

選擇 Groq 而非本地 Ollama：Groq 有免費 tier、推論速度快、不需要本地 GPU，適合 eval pipeline。

LiteLLM Function Calling：LiteLLM 支援 `tools` 參數的 OpenAI-compatible 格式。需要把 `ghibli.tools` 的 Python function 轉成 OpenAI tool schema（`name`, `description`, `parameters`）。新增 `evals/tool_schema.py` 負責這個轉換。

### run_evals.py 擴充

新增 `--model` CLI 選項（預設 `gemini`）：
```bash
uv run python evals/run_evals.py --model gpt4o-mini
uv run python evals/run_evals.py --model llama3 --category typo
```

results.json 結構修改：
- run_obj 新增 `model` 欄位
- 每筆 per-query result 新增 `judge_result`（`tool_match`, `param_match`, `sequence_match`）
- run_obj 新增 `accuracy`（pass 數 / 總數，浮點數）

### compare_models.py

讀取 results.json，group by model，計算每個模型的整體 accuracy 與各類別 accuracy，輸出 Markdown 表格到 stdout。

```bash
uv run python evals/compare_models.py
```

輸出範例：
```
| Model        | Overall | fuzzy | typo | contradiction | multilingual | multi_step |
|---|---|---|---|---|---|---|
| gemini       | 90%     | 83%   | 100% | 83%           | 100%         | 83%        |
| gpt4o-mini   | 87%     | 83%   | 83%  | 83%           | 100%         | 83%        |
| llama3       | 87%     | 67%   | 100% | 83%           | 100%         | 83%        |
```

## Risks / Trade-offs

- **Ground truth 主觀性**：multi_step 類的 `tool_sequence` 可能有多個正確答案（e.g., 先查 user 再查 repo，或直接查 repo）。設計上允許 judge 只檢查 partial sequence，不要求完全吻合。
- **LiteLLM Function Calling 相容性**：各模型對 function call 的支援程度不一，Llama 3.3 的 tool call 可能格式略有差異，`models.py` 需要處理 LiteLLM 回傳的 tool call 格式統一化。→ 先跑 smoke test，遇到格式問題在 judge 層 normalize。
- **Groq rate limit**：免費 tier 有 RPM 限制，eval 30 條查詢需在呼叫間加 delay（1 秒）。
- **API key 管理**：新增 `OPENAI_API_KEY`（GPT-4o-mini）與 `GROQ_API_KEY`（Llama 3 via Groq）到 `.env.example`。

## Open Questions

- GPT-4o-mini 的 function calling 格式與 google-genai 不同；LiteLLM 是否完全透明處理，還是需要 adapter？→ 在 `models.py` 的 smoke test task 驗證。
