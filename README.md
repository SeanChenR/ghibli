# ghibli — GitHub Intelligence Bridge

用自然語言查詢 GitHub，不需要記住 API 格式。

```
You> 搜尋最多星星的 TypeScript 前端框架
Ionic Framework 是最受歡迎的 TypeScript 前端框架，它有 52466 顆星。

You> 可以告訴我它的最新 release 嗎
Ionic Framework 最新版本是 v8.4.0，發布於 2025-03-12。
```

底層是 LLM Function Calling（Gemini / GPT-4o-mini / Gemma-4 / Ollama 可互換）→ 13 個 GitHub REST API tools → Rich Markdown 輸出。

---

## Take-Home Assessment 入口

| 項目 | 位置 |
|---|---|
| Part 1 — 執行 CLI 工具 | [使用方式](#使用方式)（`uv run ghibli`） |
| Part 1 — Break / Harden 說明 | [Eval 框架](#eval-框架) |
| Part 1 — 無法根解的案例 | [已知限制](#已知限制) |
| Part 2 — 執行 Eval Pipeline | `uv run python evals/run_evals.py --model <name>` |
| Part 2 — 多模型評測結果 | [多模型評測結果](#多模型評測結果) |

---

## 安裝

需要 Python 3.12+ 與 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/yourname/ghibli
cd ghibli
uv sync
cp .env.example .env
# 填入想用的模型 API key（見下一節）
```

---

## 支援的模型與快速配置

CLI（`agent.chat`）和 Eval pipeline（`evals/models.py`）共用同一組 13 個 tool schema，任何有 function calling 能力的模型都能接上。`.env` 只填你要用的那組即可。

### CLI 使用（`uv run ghibli`）

用 `--model` 切換，或設 `GHIBLI_MODEL` env var（`--model` 優先）：

| 模型 | `--model` 值 / `GHIBLI_MODEL` | 必填環境變數 |
|---|---|---|
| **Gemini 2.5 Flash**（預設） | 省略 或 `gemini-2.5-flash` | `GEMINI_API_KEY` |
| **Vertex AI**（Gemini 走 Google Cloud） | 省略 或 `gemini-2.5-flash` | `GOOGLE_CLOUD_PROJECT` + `gcloud auth application-default login` |
| **OpenAI**（GPT-4o-mini / GPT-4o / …） | `openai:<model>`，如 `openai:gpt-4o-mini` | `OPENAI_API_KEY` |
| **Ollama Cloud**（開源模型） | `ollama:<slug>`，如 `ollama:llama3.1:8b` | `OLLAMA_API_KEY` |

```bash
uv run ghibli --model openai:gpt-4o-mini
uv run ghibli --model ollama:llama3.1:8b
GHIBLI_MODEL=openai:gpt-4o-mini uv run ghibli     # env var 版本
```

路由規則：值以 `openai:` 或 `ollama:` 開頭時走 LiteLLM；其他值（含預設）走 Gemini 原生 SDK，此時再看 `GEMINI_API_KEY` > `GOOGLE_CLOUD_PROJECT`（Vertex）。

### Eval 使用（`uv run python evals/run_evals.py --model <name>`）

| `--model` | 後端 | 必填環境變數 |
|---|---|---|
| `gemini` | Gemini 2.5 Flash（閉源） | `GEMINI_API_KEY` |
| `gemma4` | Gemma-4-26b（開源權重，透過 Gemini API 存取） | `GEMINI_API_KEY` |
| `gpt4o-mini` | GPT-4o-mini（閉源） | `OPENAI_API_KEY` |
| `ollama-cloud` | Ollama Cloud 上任一支援 function calling 的模型 | `OLLAMA_API_KEY`（`OLLAMA_CLOUD_MODEL` 選用） |

### 只想跑 Demo？最省力組合

```bash
# 到 https://aistudio.google.com/app/apikey 申請 Gemini API Key（免費額度夠用）
echo 'GEMINI_API_KEY=AI...your_key' >> .env
uv run ghibli
```

設定 `GITHUB_TOKEN`（PAT，只需 `public_repo:read`）可將 GitHub rate limit 從 60 req/hr 提高至 5000 req/hr。

---

## 使用方式

```bash
uv run ghibli                        # 開新 session
uv run ghibli --session <id>         # 接續歷史 session
uv run ghibli --list-sessions        # 列出所有 session
uv run ghibli --json                 # 輸出原始 JSON 而非 Rich Markdown
uv run ghibli --version
```

### 範例查詢

```
可以幫我看看 Spectra-app 這個 Repo 嗎，然後跟我說一下具體這個 Repo 是在做什麼的，最近有什麼樣的更新
```

---

## 開發流程：以 Spec 驅動 Claude Code

整個專案用 [Spectra](https://github.com/kaochenlong/spectra-app)（Spec-Driven Development）切成 8 個 change，每個 change 先產出 `proposal.md` + `tasks.md` + `specs/*/spec.md`，再由 Claude Code 逐項實作。好處是：AI 不必猜整體系統設計，每次只負責一個有清楚邊界的 change；commit 粒度天然乾淨，Spec 本身就是驗收清單。歷史 change 完整保留在 `openspec/changes/archive/`。

開發順序：

| # | Change | 內容 |
|---|---|---|
| 1 | `project-scaffold` | pyproject.toml、src layout、`GhibliError` 階層、pytest 80% 覆蓋率門檻 |
| 2 | `session-manager` | SQLite `~/.ghibli/sessions.db`，兩張表 `sessions` / `turns`、CRUD API |
| 3 | `github-api-client` | `github_api.execute(tool_name, args)` 單一進入點 + `_TOOL_MAP` + `follow_redirects=True` |
| 4 | `cli-entry-point` | Typer 對話 loop、`--session` / `--list-sessions` / `--json` / `--version` |
| 5 | `github-tools` | 6 個 Python callable + Gemini Function Calling loop + 雙認證（API Key / Vertex） |
| 6 | `output-formatter` | Rich Markdown 渲染、session 歷史載回 `contents`、cli 串接 agent |
| 7 | `eval-framework` | 30 條 `queries.yaml` + `run_evals.py`，跑出第一輪 failure 集 |
| 8 | `multi-model-eval` | Tools 6 → 13、LiteLLM 接 3 個模型、加 `judge.py` / `ground_truth` / `compare_models.py`、system prompt 迭代到 100% |

每個 change 典型生命週期：

```
/spectra-discuss    討論需求、澄清邊界
  ↓
/spectra-propose    產出 proposal + tasks + spec.md（Plan Mode）
  ↓
/spectra-apply      Claude 照 tasks.md 逐項實作（TDD）
  ↓
/spectra-archive    提交 diff、把 change 搬到 archive/
```

---

## GitHub API → Tools 包裝設計

### 為什麼需要包裝成 tools

LLM 不會自己打 `GET https://api.github.com/search/repositories?q=...`，只會輸出「想呼叫哪個函數、帶什麼參數」。所以我先請 Claude 通讀 GitHub REST API 文件，挑出回答一般 GitHub 問題最常用的端點，為每個端點寫一支 Python function：

- Function 的 **signature + docstring** 就是 LLM 看到的 schema（`google-genai` 和 `litellm` 都會自動 introspect）
- Function 的 **實作** 把參數轉 HTTP 請求，統一走 `github_api.execute()`
- Function Calling loop 看到模型想呼叫哪個就 dispatch，把 JSON 回傳塞回 `contents` 再叫一次模型直到出純文字

等於在 API 文件與 LLM 之間架了一層「只暴露我想給的能力」的介面——也能避免 LLM 亂填 header 或 URL。

### 13 個 Tools（依類別）

**跨 repo 搜尋（`q` 必填，支援 GitHub Search qualifier）**

| Tool | REST 端點 | 說明 |
|---|---|---|
| `search_repositories` | `GET /search/repositories` | 主力工具；支援 `language:` / `stars:>N` / `license:` / `pushed:` / `created:` / `archived:` / `good-first-issues:` / `in:readme` 等 qualifier |
| `search_code` | `GET /search/code` | 找「哪些 repo 的哪個檔案用到某段程式碼」，支援 `repo:`/`language:`/`path:`/`filename:`/`extension:` |
| `search_users` | `GET /search/users` | 找人或組織，支援 `followers:>N` / `location:` / `type:org` |
| `search_issues` | `GET /search/issues` | 跨 repo 搜 issue / PR，支援 `is:pr` / `is:open` / `label:good-first-issue` / `author:` |

**單一 repo 查詢（`owner` + `repo` 必填）**

| Tool | REST 端點 | 說明 |
|---|---|---|
| `get_repository` | `GET /repos/{o}/{r}` | 只回 metadata（star / fork / primary language 字串等） |
| `get_readme` | `GET /repos/{o}/{r}/readme` | base64 decode 的 README 文字（超過 3000 字截斷） |
| `get_languages` | `GET /repos/{o}/{r}/languages` | 完整語言 byte 分布（`get_repository` 只給主要語言字串） |
| `list_issues` | `GET /repos/{o}/{r}/issues` | 列單一 repo 的 issue |
| `list_pull_requests` | `GET /repos/{o}/{r}/pulls` | 列單一 repo 的 PR |
| `list_releases` | `GET /repos/{o}/{r}/releases` | Release 清單與發布日期 |
| `list_commits` | `GET /repos/{o}/{r}/commits` | Commit 歷史，可帶 `sha` / `author` 過濾 |
| `list_contributors` | `GET /repos/{o}/{r}/contributors` | 貢獻者排行（依 commit 數） |

**單一使用者查詢**

| Tool | REST 端點 | 說明 |
|---|---|---|
| `get_user` | `GET /users/{username}` | 個人公開資訊、follower 數、公開 repo 數 |

### 關鍵設計取捨

- **`search_*` vs `list_*` 嚴格分工**：前者跨 repo、`q` 必填；後者只吃 `owner + repo`。名稱相近但語意差很遠，模型很容易搞混（實際 eval failure 2 就是這個），所以 system prompt 逐條明列使用與禁止場景。
- **`get_repository` 不 inline README / 完整語言分布**：維持 REST API 原設計；要讀 README 用 `get_readme`，要完整語言 byte 分布用 `get_languages`，避免單一 tool 回傳結構暴漲而讓模型迷路。
- **所有 tool 回傳 `dict | list`**：原樣丟 LLM 自己摘要，程式層不壓欄位——少一層人為耦合，不同查詢能自由 emphasize 不同欄位。

---

## 架構

```
自然語言輸入
     ↓
cli.py（Typer 對話 loop）
     ↓
agent.py（Function Calling loop；分兩條路：Gemini 原生 SDK 或 LiteLLM）
     ↓  ← append_turn / get_turns
sessions.py（SQLite ~/.ghibli/sessions.db）
     ↓
tools.py（13 個 GitHub tool function）
     ↓
github_api.py（httpx → api.github.com，follow_redirects=True）
     ↓
output.py（Rich Markdown / JSON 輸出）
```

幾個選擇的理由：

- **Function Calling（而非 prompt + JSON 解析）**：SDK 自動驗型別、支援多步 agent loop、eval 可以直接從 `response.function_calls` 讀出被呼叫的 tool 序列，不用再解析 LLM 文字輸出。
- **手動停用 `automatic_function_calling`**：為了可觀測。eval 需要在自己 dispatch 的地方記錄 tool 序列，自動模式下整條 loop 在 SDK 內部，外面拿不到。
- **SQLite 而非記憶體 / JSONL**：CLI 會被啟動多次，要能「接上一次對話」；檔案 DB 最簡單、零配置。表結構做成 `sessions + turns` 是為了之後 eval 能以 SQL 跨 session 查詢 tool call 記錄。

---

## Eval 框架

```
evals/
├── queries.yaml        # 30 條測試案例（6 category × 5）
├── run_evals.py        # 逐題跑，寫入 results.json
├── models.py           # LiteLLM 包裝，切 4 個 eval 後端
├── judge.py            # 比對 tools_called vs ground_truth
├── compare_models.py   # 跨模型 accuracy Markdown 表
└── results.json        # 歷次 run 結果（含 response 全文）
```

### 執行

```bash
uv run python evals/run_evals.py --model gemini
uv run python evals/run_evals.py --model gpt4o-mini
uv run python evals/run_evals.py --model gemma4
uv run python evals/run_evals.py --model gemini --category typo   # 只跑某類
uv run python evals/compare_models.py                              # 跨模型比較表
```

### 30 條 Query 分類

| 類別 | 數量 | 測什麼 |
|---|---|---|
| `qualifier` | 5 | 自然語意 → GitHub Search qualifier（`license:mit`、`archived:false`、`good-first-issues:>10`、`in:readme` …） |
| `temporal` | 5 | 時間推理（`pushed:` vs `created:`、`..` 範圍語法、相對日期換算） |
| `typo` | 5 | org / repo / language 拼字錯誤自動修正（含 `flaskk` → pallets/flask 的 org 推斷） |
| `contradiction` | 5 | 邏輯不可能條件（含一條 TRAP：`star >> fork` 其實正常，模型不該拒絕） |
| `multi_step` | 5 | 需要 2–3 個 tool 串接 |
| `tool_selection` | 5 | 每條都有誘人的錯誤工具（核心 hardening） |

### Ground Truth 與判斷標準

每條 query 有一組 `ground_truth`，`evals/judge.py` 只檢查 tool 名稱與順序：

```yaml
# 單一工具
ground_truth:
  tool: search_repositories     # expected_tool 必須出現在 tools_called

# 多步驟（允許中間插入其他呼叫，但順序正確）
ground_truth:
  tool: list_commits
  tool_sequence:                # 對 tools_called 做 subsequence match
    - get_repository
    - list_commits

# 不該呼叫任何工具
ground_truth:
  tool: none                    # tools_called 必須為空
```

刻意不檢查 `q` 字串內容：`q="stars:>5000 language:rust"` 和 `q="language:rust stars:>5000"` 等價；GitHub Search 也允許多種等價表達。過嚴的檢查會把對的答案誤判成錯，反而測不到「模型懂不懂得選工具」這件事。

### Eval 設計演進

- **v1**：30 條、5 categories × 6，問題太簡單，三個模型大多一輪就達 96.7%+，拉不出差異。
- **v2**：擴到 37 條加測新工具，但新增的 `extended` query 缺乏誘人錯誤選項，還是太好過。
- **v3（現行）**：30 條、6 categories × 5，用 `tool_selection` 取代 `extended`。每條刻意放一個「看起來對但其實錯」的工具，並加入 TRAP contradiction（star >> fork 是正常）避免過度保守。

> **仍可補的缺口**：`list_contributors` 是 13 個 tool 裡唯一沒被任何 query 觸發到的；多語言也只保留繁中 + English 混用，v2 原有的日/韓文在取捨時被換掉了。目前 100% 通過率下不是 blocker，未來擴充 eval 時可以補。

### 失敗案例與 System Prompt 設計

System prompt 集中在 `src/ghibli/prompt.py` 的 `get_system_prompt()`，CLI（`agent.py`）和 eval（`evals/models.py`）共用同一份，eval 固定日期 `2026-04-22` 以保可重現、CLI 用今天日期。初版只有兩三行，下面每個區塊都是被一個實際 failure 逼出來的。

#### Failure 1 — Gemini 直接從訓練資料回答（qualifier-003）

**Query**：「找 README 裡有提到 `zero dependencies` 的輕量 JavaScript 工具」

Gemini 沒呼叫工具，直接背出一串 repo 名。Ground truth 要求必須呼叫 `search_repositories`，判為 fail。

**修復**：加 `## Always use tools — never answer from training data`，強制任何 GitHub 相關問題都必須查實際資料。

#### Failure 2 — GPT-4o-mini 工具邊界混淆（tool_selection-002）

**Query**：「找所有 Python repo 裡開放中、標記 good-first-issue 的 issue」

模型選了 `list_issues`，但它只能查單一 repo；跨 repo 要用 `search_issues`。

**修復**：加 `## Tool selection — critical rules`，逐條列每個 tool 的使用場景與禁止場景（例：`list_issues` 禁止用於跨 repo 搜尋）。

#### Failure 3 — 矛盾條件仍先呼叫工具驗證（contradiction-004）

**Query**：「找 fork 數是 star 數 1000 倍的熱門 JavaScript 框架」

GPT-4o-mini 明知不可能，還是先呼叫 `search_repositories` 證明結果為空才解釋。Ground truth 是 `tool: none`，所以 fail。

**修復**：用強制語氣「**MUST** respond with explanation only — never call any tool, not even to verify」，並列出具體不可能條件（star > 500k、fork > 10× star、未來年份、PR 同時 open 又 closed …）。同步加入 TRAP query 區分「fork >> star 不可能」 vs 「star >> fork 正常」，防止加規則後變得過度保守。

#### Failure 4 — multi-step 跳過明確要求的 step（multi_step-003）

**Query**：「找 star 最多的 Go web framework，先取得它的 repo 資訊，再看最近有哪些 release」

`search_repositories` 結果本來就含 owner/repo，模型覺得 `get_repository` 冗餘就跳過。但 ground truth sequence 要求三步都在。

**修復**：列出具體中文觸發短語（`取得 repo 資訊`、`先取得它的資訊`、`repo details`），規定即使已知 owner/repo 也必須呼叫。

#### 每條 prompt 規則都對應一個 failure

| System prompt 區塊 | 對應 failure |
|---|---|
| `Always use tools` | qualifier-003（從訓練資料回答） |
| `Typo correction and unknown owners` | typo-001~005（用錯拼字打 API）+ 使用者只給 repo 名未給 owner（`spectra-app`）→ 先 search 再 call |
| `search_repositories q is always required` | fuzzy query 不帶 `q` → SDK validation error |
| `Tool selection — critical rules` | tool_selection-002（`list_issues` 跨 repo 誤用） |
| `Multi-step queries` | multi_step-003（跳過要求的 `get_repository`） |
| `Contradictory or impossible conditions` | contradiction-001~004（仍去 verify） |
| `stars >> forks is normal` | contradiction-005 TRAP（過度保守會 fail） |
| `Language — reply in user's language` | 早期 multilingual eval 偶爾用英文回日文 |

完整 hardening log 見 [`specs/eval-hardening-log.md`](specs/eval-hardening-log.md)。

### Eval 設計心得

- **Ground truth 只標 tool 名與順序，不標 `q` 字串細節**：等價參數多種寫法都對，過嚴的判斷會誤判對的答案。
- **TRAP query 很重要**：加「MUST not call tool」規則後，模型會變得過度保守把正常查詢也拒絕；需要「看似矛盾但其實正常」的 query 作反向保險。
- **每條 prompt 規則都該對應一個實際 failure**：憑空想像的規則容易 overfit 不存在的問題；「看到 failure 才加規則」讓每條都有驗收條件，可以逐條回歸。
- **System prompt 不宜無限擴張**：越加規則越容易誤觸相鄰規則。所以遇到新失敗偏好加 TRAP / 例子，而非再疊新的 "MUST"。

---

## 多模型評測結果

| Model | Overall | Qualifier | Temporal | Typo | Contradiction | Multi-Step | Tool Selection |
|-------|---------|-----------|----------|------|---------------|------------|----------------|
| gemini-2.5-flash | **100%** | 100% | 100% | 100% | 100% | 100% | 100% |
| gpt-4o-mini | **100%** | 100% | 100% | 100% | 100% | 100% | 100% |
| gemma-4-26b | **100%** | 100% | 100% | 100% | 100% | 100% | 100% |

達成 PDF 要求的「至少 3 個模型、開源 + 閉源 mix、>85% threshold」。

### 模型選型理由

| Model | 類型 | 為什麼選 |
|---|---|---|
| **gemini-2.5-flash** | 閉源 | CLI 主模型、eval baseline；Function Calling 最穩 |
| **gpt-4o-mini** | 閉源 | OpenAI 最便宜仍支援 function calling 的模型，代表「便宜夠用」選項 |
| **gemma-4-26b** | **開源權重** | Google 開放的 open-weight 模型，透過 Gemini API 存取避開本機資源限制 |

`ollama-cloud` 接口在 CLI 與 eval 兩邊都可用。`qwen3.5:cloud` 實測能穩定做 function calling（單條 query 推理 60–90 秒），早期試過的 `minimax-m2.7:cloud` 會回空回應、`llama3.1:8b` 單條超過數分鐘。CLI 使用：`--model ollama:qwen3.5:cloud`；Eval：`OLLAMA_CLOUD_MODEL=qwen3.5:cloud uv run python evals/run_evals.py --model ollama-cloud`。

---

## 測試

109 條測試、整體覆蓋率 88%，由 `pyproject.toml` 強制 `--cov-fail-under=80` 門檻。單元測試 mock 掉外部依賴（`litellm.completion`、`genai.Client`、`httpx`、SQLite）；整合測試用 `@pytest.mark.integration` 標記、真的打外部 API。

```bash
uv run pytest                           # 預設全跑
uv run pytest -m "not integration"      # 只跑 unit（適合 CI，無外網依賴）
uv run pytest tests/integration/        # 只跑整合測試
```

| 檔案 | 類型 | 數量 | 測什麼 |
|---|---|---|---|
| `test_agent.py` | Unit | 16 | Gemini SDK + LiteLLM 雙路徑 routing；`--model` 覆寫 `GHIBLI_MODEL` env；`openai:` / `ollama:` prefix 解析；tool 失敗可恢復（error 塞回給 LLM 不 raise）；session turn 持久化 |
| `test_cli.py` | Unit | 10 | Typer 對話 loop；`--version` / `--list-sessions` / `--json` / `--session` / `--model` flag；空行 / EOF 優雅退出；`GhibliError` 不中斷 session；未知 session id 拒絕 |
| `test_github_api.py` | Unit | 9 | `execute()` URL path 參數替換；`GITHUB_TOKEN` Authorization header；User-Agent；404 / 500 / timeout → `GitHubAPIError`；unknown tool → `ToolCallError` |
| `test_tools.py` | Unit | 13 | 13 個 tool 函式 imports；參數轉發到 `github_api.execute()`；`list_commits` 略過 `None` optional；`get_readme` base64 解碼 + 3000 字截斷 + 非 base64 回原樣 |
| `test_tool_schema.py` | Unit | 4 | Python docstring + type hint → OpenAI-compatible schema 轉換；13 tools 全列；schema 結構合法（type/properties/required） |
| `test_sessions.py` | Unit | 11 | `~/.ghibli/sessions.db` 首次自動建立；UUID session id；CRUD（get / list / append）；turn 含 tool metadata；空 session 回空；插入順序保留 |
| `test_exceptions.py` | Unit | 8 | `GhibliError` 為基類；所有子類可統一 catch；`GitHubAPIError` 帶 status code；`ToolCallError` / `SessionError` / `OutputError` 繼承關係 |
| `test_output.py` | Unit | 4 | `render_text()` 非空字串；空字串 fallback 為 `(no response)`；Rich Markdown 渲染路徑；`--json` 包 `{"response": ...}` |
| `test_eval_queries.py` | Unit | 5 | `queries.yaml` YAML 可解析；每條必填欄位存在；`category` 合法；`ground_truth` 全員標註；`multi_step` 有 `tool_sequence` |
| `test_eval_runner.py` | Unit | 9 | `run_query()` pass / fail / error 分類；結果 append 不覆蓋；`--category` filter；`judge_result` 嵌入；`--model` 記錄；accuracy 為 float；unknown model 退出非 0 |
| `test_judge.py` | Unit | 8 | 單一 tool match / mismatch；順序正確 / 逆序 fail；`tool: none` 哨兵；non-contiguous subsequence 過 |
| `test_models.py` | Unit | 8 | `evals/models.py` LiteLLM wrapper：4 個模型 model_id resolution；unknown model / 缺 API key → `ToolCallError`；回傳 `(str, list[str])` |
| `test_compare_models.py` | Unit | 3 | 跨模型比較 Markdown 表產生：3 列資料；accuracy 顯示為小數點後 1 位百分比；缺席模型不產生 row |
| `test_github_api_integration.py` | **Integration** | 1 | 活打 `api.github.com` 的 `search_repositories("python")`，驗證實際 JSON 結構、CI 預設跳過 |

**為什麼沒追 100% 覆蓋率**

剩下的 ~12% 主要在三類 code：

- **連線 / rate limit / timeout 錯誤分支**：要測得 mock `litellm.exceptions.RateLimitError` + 偽造 Retry-After，寫起來腐爛快、回報低
- **SQLite CRUD 的「session 不存在」early return**：測了只是證明 `if row is None: return None`
- **13 個 tool wrapper 的 `return github_api.execute(...)` 轉發層**：結構一致，測頭尾的範本已足以保證其餘相同

業界共識 80% 是 sweet spot；投入 80% → 100% 所需時間和 0% → 80% 相當，但抓到的 bug 只多 2–5%。這個專案刻意停在 88%，把心力花在 eval 的 30 條 ground truth 上反而更實際。

---

## 已知限制

### 1. 模糊輸入只能近似

GitHub REST API 沒有官方 trending endpoint。ghibli 用 `created:>{近期} sort:stars` 近似「最近很紅」，能找到 OpenClaw、Hermes Agent 等合理結果，但 star 增速快而 created 時間較早的 repo 會被漏掉。這是 API 本身的限制，prompt 無解。

### 2. 矛盾條件判斷依賴 LLM 推理

GitHub API 對「fork > star × 1000」這種不可能條件會照單全收回空結果。ghibli 靠 prompt 和模型推理識別，eval 中 5 條 contradiction 都能正確拒絕，但這是統計性而非程式保證——引入推理較弱的模型時此保證會鬆動。

### 3. Typo 修正有邊界

Typo correction 同樣依賴 LLM，沒有規則式字典。語意歧義時（`linus` 可能是人名也可能是 `linux` 的縮寫）仍可能往錯方向修正。

### 4. 非繁中多語言未正式驗證

現行 30 條全是繁中 + English 混用；日文、韓文在 v2 做過但 v3 沒納入正式 ground truth。複雜多步驟的日韓查詢準確性不保證。

---

## 開發指令

```bash
uv run pytest                      # 執行測試（含 80% 覆蓋率門檻）
uv run ruff check src/
uv run black src/ tests/
```
