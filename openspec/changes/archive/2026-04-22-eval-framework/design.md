## Context

ghibli Phase 1 的核心流程（自然語言 → Gemini Function Calling → GitHub API → 輸出）已完成並通過 unit tests。但 unit tests 全部使用 mock，從未以真實 LLM 回應驗證邊緣案例的行為。

現有的測試覆蓋率（87%）只驗證了程式碼路徑，無法反映 Gemini 面對模糊、錯誤或非英文輸入時的實際表現。

## Goals / Non-Goals

**Goals:**

- 定義一套可重現的 eval 查詢格式（YAML）
- 實作執行器腳本，能批次跑查詢、記錄每條的工具呼叫與輸出、標記 pass/fail/error
- 以 `evals/results.json` 儲存快照，作為 Phase 2 優先順序決策的依據
- 在 README 記錄根本難以解決的失敗類別及原因

**Non-Goals:**

- 不在 `src/` 修改任何核心邏輯
- 不建立 CI 整合（eval 需要真實 API key）
- 不對每條查詢定義唯一正確答案（模糊查詢的「正確」本身就是主觀的）

## Decisions

### 查詢格式：YAML 而非 Python hardcode

選擇 `evals/queries.yaml` 而非直接寫在 Python 檔案裡。

原因：
- YAML 可讀性高，非技術人員也能新增測試案例
- 格式與程式碼分離，修改查詢不需動程式碼
- 結構可以帶 metadata（category、expected_behavior、difficulty）

替代方案考慮過：JSON（冗長、無法寫註解）、CSV（太扁平，無法嵌 metadata）。

查詢格式：
```yaml
- id: fuzzy-001
  category: fuzzy          # fuzzy | typo | contradiction | multilingual | multi_step
  query: "找個好用的前端框架"
  expected_behavior: "calls search_repositories with some frontend-related query"
  difficulty: hard          # easy | medium | hard
  notes: "模糊輸入，沒有明確語言或條件，Gemini 需要自行猜測"
```

### 執行器：直接呼叫 agent.chat()，不繞過 Gemini

執行器透過 `from ghibli.agent import chat` 呼叫真實的 Function Calling 流程，而非 mock。

原因：eval 的目的就是觀察真實行為，mock 掉 Gemini 就失去意義。

每次執行會記錄：
- `query_id`、`category`、`query`
- `status`：`pass` / `fail` / `error`
- `tools_called`：實際呼叫了哪些 tool（list）
- `response_preview`：回應前 200 字元
- `error_message`：若 status=error 時的例外訊息
- `duration_seconds`：呼叫耗時
- `timestamp`：執行時間

### 結果儲存：append 模式，保留歷史

`results.json` 採用 append 模式，每次執行在頂層陣列加入一個 run 物件：
```json
[
  {
    "run_id": "2026-04-22T05:00:00",
    "results": [...]
  }
]
```

原因：保留多次執行的歷史，才能觀察修改後行為是否改善。

### 五個測試類別及各 6 條查詢

| 類別 | 數量 | 代表性問題 |
|---|---|---|
| `fuzzy` | 6 | 沒有明確條件的模糊查詢 |
| `typo` | 6 | 常見拼字錯誤（語言名稱、工具名稱） |
| `contradiction` | 6 | 邏輯上不可能或自相矛盾的條件 |
| `multilingual` | 6 | 日文、韓文輸入 |
| `multi_step` | 6 | 需要兩次以上 tool call 的查詢 |

### pass/fail 判斷標準

由於沒有唯一正確答案，pass/fail 以以下規則判斷：
- `pass`：有回應文字且無例外（不論回應品質）
- `fail`：回應為空或 Gemini 明確說無法處理（包含「無法理解」類回應）
- `error`：拋出例外（ToolCallError、GitHubAPIError 等）

實際回應品質記錄在 `response_preview`，由人工判讀。

### README 已知限制章節

新增於 README 的「已知限制」章節說明以下三類根本困難：

1. **模糊輸入**：沒有明確 API 參數對應，Gemini 只能猜測，結果不可預測
2. **矛盾條件**：GitHub API 本身無法回傳，Gemini 可能仍然呼叫 API 並得到空結果，而不是提前拒絕
3. **多語言**：Gemini 支援多語言，但中文以外的語言（日文、韓文）未測試，行為未知

## Risks / Trade-offs

- **API 費用**：30 條查詢 × 1 次執行約消耗少量 Gemini tokens，但若頻繁跑 eval 需注意費用
  → Mitigation：`run_evals.py` 支援 `--category` 過濾，可只跑特定類別

- **結果不穩定性**：同一條查詢跑兩次可能得到不同結果（LLM 非確定性）
  → Mitigation：記錄 timestamp，多次執行結果都保留在 results.json，以觀察趨勢而非單次結果

- **GitHub API rate limit**：30 條查詢可能觸發 GitHub 的未認證限制（60 req/hr）
  → Mitigation：建議執行前設定 `GITHUB_TOKEN`；runner 如果遇到 GitHubAPIError 標記為 error 而非 fail
