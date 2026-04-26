# Roadmap — ghibli

## 開發哲學

先讓核心流程跑起來，再強化邊緣情況，最後才做評測。  
每個 Phase 完成後，下一個 Phase 才開始。Phase 2 的輸出 schema 穩定性是 Phase 3 的前提。

---

## Phase 1 — 核心 CLI（基礎功能）✅ 已完成

**目標**：讓自然語言查詢 GitHub 這件事「能跑」

### 實作內容

- 互動式對話 loop：執行 `ghibli` 後進入 prompt，支援 `--session` 接續歷史
- Gemini 2.5 Flash Function Calling：自行決定呼叫哪個 GitHub tool、呼叫幾次
- 6 個 GitHub tools：`search_repositories`、`get_repository`、`list_issues`、`list_pull_requests`、`get_user`、`list_releases`
- 輸出：預設 Rich Markdown，`--json` 輸出 `{"response": "..."}`
- Session 持久化：對話歷史存於 `~/.ghibli/sessions.db`，多輪追問有效

### 完成條件

- [x] 能處理 6 種 GitHub API 操作（搜尋、repo 詳情、issues、PRs、releases、user）
- [x] 輸出格式一致、可讀（Rich Markdown，中文 Unicode 保留）
- [x] 基本錯誤不會 crash（Gemini APIError、GitHubAPIError 均捕捉，逐輪顯示友善訊息）
- [x] 多輪對話：session history 正確載入，追問有效（已 E2E 驗證）

---

## Phase 2 — 強化層（Hardening）

**目標**：讓工具「用起來不會崩」，並建立穩定的輸出 schema

> ⚠️ Phase 2 的輸出 schema 穩定性至關重要，因為 Phase 3 的 ground truth 標注依賴於此。

### 功能範疇

- **輸入清洗**：過濾特殊字元、避免 prompt injection
- **Typo 容錯**：常見錯字仍能正確解析（如 `repositry` → `repository`）
- **多語言支援**：英文與繁體中文輸入都能處理，輸出語言跟隨輸入
- **模糊查詢 fallback**：當意圖不明確時，主動詢問使用者澄清問題
- **錯誤處理**：對無效查詢、無法解析的意圖提供友善的錯誤訊息
- **輸出 schema 鎖定**：定義並凍結 API 回應的結構，為 ground truth 標注做準備

### 完成條件

- [ ] 通過 20 條邊緣案例測試（含中文、typo、模糊查詢）
- [ ] 輸出 schema 文件化，版本鎖定
- [ ] 所有錯誤情境都有對應的使用者友善訊息

---

## Phase 3 — 多模型評測 Pipeline

**目標**：建立可重現的 NL-to-API 評測框架，評測多個 LLM 的表現

> 前提：Phase 2 完成，輸出 schema 穩定。

### 功能範疇

- **測試資料集**：30 條多元自然語言查詢
  - 涵蓋邊緣案例、模糊表達、複雜條件、多步驟查詢
  - 手動標注 ground truth（正確 GitHub API endpoint + params）
- **多模型整合**（透過 LiteLLM 統一介面）：
  - Gemini（閉源）
  - GPT-4o（閉源）
  - Llama 3 via Ollama（開源權重）
- **評測指標**：endpoint 準確率、params 完整性、整體準確率
- **迭代 prompt 工程**：針對表現不佳的模型調整 prompt，直到所有模型準確率 > 85%
- **分析報告**（README）：
  - 模型選型建議
  - 各模型效能比較
  - 評測設計心得與限制

### 完成條件

- [ ] 30 條測試查詢全部標注完畢
- [ ] 3+ 模型都跑過評測
- [ ] 所有模型準確率 > 85%
- [ ] README 分析報告完成

---

## 時程依賴

```
Phase 1 ──完成──▶ Phase 2 ──schema 穩定──▶ Phase 3
```

Phase 3 的評測設計可以在 Phase 2 進行中開始規劃，但不可在 Phase 2 schema 確定前開始標注 ground truth。
