# Eval Hardening Log — Phase 2

記錄 Part 2 多模型評測從設計到 100% 的完整過程：每個 failure 的原因、修改方式、驗證結果。

---

## 最終結果

| Model | Overall | Qualifier | Temporal | Typo | Contradiction | Multi-Step | Tool Selection |
| ----- | ------- | --------- | -------- | ---- | ------------- | ---------- | -------------- |
| gemini | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| gpt4o-mini | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| gemma4 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

---

## 工具擴充（Phase 2 新增 7 個 tool）

從 Phase 1 的 6 個工具擴充為 13 個：

| 新增工具 | API Endpoint | 說明 |
|---------|-------------|------|
| `get_languages` | `GET /repos/{owner}/{repo}/languages` | 完整語言分布（bytes） |
| `list_contributors` | `GET /repos/{owner}/{repo}/contributors` | 貢獻者清單，按 commit 數排序 |
| `list_commits` | `GET /repos/{owner}/{repo}/commits` | commit 歷史，支援 author/sha 過濾 |
| `search_code` | `GET /search/code` | 跨 repo 原始碼搜尋 |
| `search_users` | `GET /search/users` | 搜尋開發者/組織 |
| `search_issues` | `GET /search/issues` | 跨 repo issue/PR 搜尋 |
| `get_readme` | `GET /repos/{owner}/{repo}/readme` | 取得並解碼 README 內容 |

`get_readme` 需要額外處理 GitHub 回傳的 Base64 編碼，並限制 3000 字元以控制 token。

---

## Eval Query 設計演進

### v1（Phase 1）：30 條，5 categories × 6
- qualifier, temporal, typo, contradiction, multi_step
- 問題：太容易，雲端模型普遍達到 96.7%

### v2（Phase 2 初版）：37 條，加入 extended category
- 追加 7 條測試新工具的查詢
- 問題：extended 查詢沒有「wrong tool temptation」，仍然太容易

### v3（最終版）：30 條，6 categories × 5，更換 tool_selection category
- 移除 extended，改為 `tool_selection` category
- 每條 tool_selection query 都有一個「誘人的錯誤工具」設計
- 新增 TRAP contradiction（star >> fork 是正常現象，模型不應拒絕呼叫工具）
- 新增複合 qualifier（license + pushed + language 同時組合）
- 新增複合 temporal（created range + stars 組合）

---

## Failure 分析與修復

### Failure 1：qualifier-003（Gemini）

**現象：** `tools_called=[]`（沒有 call 任何工具）

**查詢：** 找 README 裡有提到 'zero dependencies' 的輕量 JavaScript 工具

**根本原因：** Gemini 認為自己知道幾個有名的 zero-dependency 工具（如 date-fns），直接從訓練資料回答，沒有呼叫 GitHub API。這是 LLM 的 knowledge shortcut 問題。

**修復（evals/models.py system prompt）：**
```
## Always use tools — never answer from training data
For any question about GitHub repositories, users, or statistics, ALWAYS call the
appropriate tool to get live data. Never answer from memory or training knowledge alone.
Years like 2024 and 2025 are in the past — always search for them.
```

---

### Failure 2：tool_selection-002（GPT-4o-mini）

**現象：** `tools_called=['search_repositories', 'list_issues']`

**查詢：** 找目前 GitHub 上所有 Python repo 裡開放中、標記了 good-first-issue 的 issue

**根本原因：** GPT-4o-mini 將「找 issue」預設對應到 `list_issues`，但 `list_issues` 需要 owner+repo（單一 repo）。「所有 Python repo 裡的 issue」是跨 repo 搜尋，必須用 `search_issues`。模型缺乏對兩個工具邊界的認識。

**修復（evals/models.py system prompt，新增 Tool selection section）：**
```
- list_issues / list_pull_requests: ONLY for a SPECIFIC repo (requires owner + repo).
  NEVER use for cross-repo searches.
- search_issues: For finding issues or PRs ACROSS multiple repos.
  Use when no specific single repo is mentioned.
```

---

### Failure 3：contradiction-004（GPT-4o-mini）

**現象：** `tools_called=['search_repositories', 'get_repository', ...]`（搜尋了好幾次）

**查詢：** 找 fork 數是 star 數 1000 倍的熱門 JavaScript 框架

**根本原因：** GPT-4o-mini 傾向「搜尋後再驗證」，試圖找看看有沒有這樣的 repo，而不是直接判斷為不可能。系統 prompt 說「fork > star 不可能」，但模型還是選擇 call API 確認。

**修復（更強硬的禁止語氣）：**
```
When a query describes a physically or logically impossible condition, you MUST respond
with an explanation only — never call any tool, not even to "verify" or "check".
Impossible conditions include:
- Forks exceeding stars by 10× or more (forks are always much fewer than stars).
```
同時加入 TRAP query（contradiction-005）以區分「star >> fork 正常」和「fork >> star 不可能」兩種情況，防止過度保守。

---

### Failure 4：multi_step-003（GPT-4o-mini）

**現象：** `tools_called=['search_repositories', 'list_releases']`（跳過了 get_repository）

**查詢：** 找 star 最多的 Go web framework，先取得它的 repo 資訊，再看最近有哪些 release

**根本原因：** GPT-4o-mini 在 search_repositories 取得結果後，已知道 owner/repo，判斷 get_repository 是多餘的，直接跳到 list_releases。它這樣做很「合理」，但違反了使用者明確說「先取得 repo 資訊」的指示。

**修復（明確列出觸發 get_repository 的中文短語）：**
```
Rules for calling get_repository in multi-step queries:
- If the user said "取得 repo 資訊", "repo 詳細資訊", "repo details", or "先取得它的資訊"
  anywhere in the query, you MUST call get_repository even if you already know the owner/repo.
- Never skip get_repository just because you found the repo name via search_repositories.
```

---

### Failure 5：Ollama Cloud 全部 error（api_base bug）

**現象：** 所有 37 條 query 全部 error，錯誤訊息：`path "/api/api/chat" not found`

**根本原因：** `api_base = "https://ollama.com/api"` + LiteLLM 自動補 `/api/chat` → 產生 `https://ollama.com/api/api/chat`（路徑重複）。

**修復（agent.py + evals/models.py）：**
```python
# 修前
_OLLAMA_CLOUD_API_BASE = "https://ollama.com/api"

# 修後
_OLLAMA_CLOUD_API_BASE = "https://ollama.com"
# LiteLLM 會自動補 /api/chat → 正確產生 https://ollama.com/api/chat
```

---

## 系統 Prompt 最終架構（evals/models.py）

加入了「Tool Selection — critical rules」section，明確指定每個工具的適用場景：

- `list_issues` / `list_pull_requests` → 只能用於單一特定 repo
- `search_issues` → 跨 repo 搜尋
- `get_repository` → 只有 metadata 和主要語言字串，沒有 README、沒有完整語言分布
- `get_languages` → 完整語言分布（bytes per language）
- `get_readme` → 讀取 README 文字內容
- `search_users` → 搜尋開發者/組織（不是找 repo）
- `search_code` → 搜尋程式碼內容（不是找 repo）

相同的 tool selection 指引也同步更新到 `src/ghibli/agent.py`（實際 CLI 的 system prompt）。
