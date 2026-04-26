# ghibli — GitHub Intelligence Bridge

自然語言 → LLM Function Calling → GitHub REST API → Rich Markdown 輸出的 CLI 工具。

工程分三階段：**Build**（CLI + 13 個 GitHub tool + function calling loop）→ **Break & Harden**（刻意打破 + prompt / pipeline 迭代）→ **Multi-Model Eval**（3 個 model × 30 題驗證，全員 ≥ 85%）。

**最終結果**：`gemini-3-flash-preview` **96.7%** · `gemma-4-26b` **90.0%** · `gpt-5.1` **86.7%**（30 題 × 3 model = 90 runs，全員過 85% threshold）。

**Demo**：

![gh](https://raw.githubusercontent.com/SeanChenR/img_gif/main/myimage/1777136625000yka5oy.png)

---

## 目錄

- [ghibli — GitHub Intelligence Bridge](#ghibli--github-intelligence-bridge)
  - [目錄](#目錄)
  - [快速開始](#快速開始)
  - [Build a Tool](#build-a-tool)
    - [架構總覽](#架構總覽)
    - [CLI 使用方式](#cli-使用方式)
    - [模型與 picker](#模型與-picker)
    - [13 個 GitHub API Tools](#13-個-github-api-tools)
    - [Spec-Driven 開發流程](#spec-driven-開發流程)
  - [Break \& Harden](#break--harden)
    - [Break：發現的失敗模式](#break發現的失敗模式)
    - [Harden：prompt 與 pipeline 迭代](#hardenprompt-與-pipeline-迭代)
    - [仍無法根解的限制](#仍無法根解的限制)
      - [1. GitHub 命名差異（compare-005 代表案例）](#1-github-命名差異compare-005-代表案例)
      - [2. 沒有官方 trending endpoint](#2-沒有官方-trending-endpoint)
      - [3. 矛盾條件判斷依賴 LLM 推理](#3-矛盾條件判斷依賴-llm-推理)
      - [4. 非中英多語言覆蓋稀疏](#4-非中英多語言覆蓋稀疏)
      - [5. Judge 是結構級、非語義級](#5-judge-是結構級非語義級)
  - [Multi-Model Eval](#multi-model-eval)
    - [Pipeline 概觀](#pipeline-概觀)
    - [Data Generation：30 條 query 設計](#data-generation30-條-query-設計)
    - [Validation Set 怎麼產 + 怎麼 Audit](#validation-set-怎麼產--怎麼-audit)
      - [30 題的取材](#30-題的取材)
      - [在 30 格裡擠 diversity 的規則](#在-30-格裡擠-diversity-的規則)
      - [Ground-Truth 怎麼 audit](#ground-truth-怎麼-audit)
    - [Ground Truth 設計](#ground-truth-設計)
    - [Judge 邏輯](#judge-邏輯)
    - [Model Selection](#model-selection)
    - [迭代過程：怎麼推到 ≥85%](#迭代過程怎麼推到-85)
      - [Phase 1 — v1 query 太簡單：100% / 100% / 100%](#phase-1--v1-query-太簡單100--100--100)
      - [Phase 2 — v2 query 改 6 scenario，三模型崩盤](#phase-2--v2-query-改-6-scenario三模型崩盤)
      - [Phase 3 — Prompt 迭代：上推到 70-83%](#phase-3--prompt-迭代上推到-70-83)
      - [Phase 4 — Judge 放寬：subsequence → multiset](#phase-4--judge-放寬subsequence--multiset)
      - [Phase 5 — Gemini 2.5 Flash → 3 Flash preview](#phase-5--gemini-25-flash--3-flash-preview)
      - [最終達成：完整軌跡](#最終達成完整軌跡)
    - [執行與結果](#執行與結果)
      - [4 個 metric 的 prompt 跟 threshold](#4-個-metric-的-prompt-跟-threshold)
      - [跨 Judge 結論（30 題 × 3 model = 90 runs）](#跨-judge-結論30-題--3-model--90-runs)
      - [結構級 per-category 細項](#結構級-per-category-細項)
    - [Performance Analysis](#performance-analysis)
      - [最終 3 個 model 的初始失敗模式（harden 前）](#最終-3-個-model-的初始失敗模式harden-前)
      - [Harden 後的差異模式](#harden-後的差異模式)
      - [有趣觀察](#有趣觀察)
    - [跨 Judge Disagreement 細節](#跨-judge-disagreement-細節)
      - [(a) 結構 PASS、語意 FAIL：模型呼叫對工具但答得不好](#a-結構-pass語意-fail模型呼叫對工具但答得不好)
      - [(b) 結構 FAIL、語意 PASS：GT 太嚴，模型實際答對了](#b-結構-fail語意-passgt-太嚴模型實際答對了)
      - [語意級判分的限制](#語意級判分的限制)
    - [Synthesizer 自動生題的對照實驗](#synthesizer-自動生題的對照實驗)
  - [單元測試 \& 整合測試 ( 基於 Test Driven Development; TDD )](#單元測試--整合測試--基於-test-driven-development-tdd-)
  - [開發指令](#開發指令)

---

## 快速開始

需要 Python 3.12+ 與 [uv](https://docs.astral.sh/uv/)。

```bash
git clone https://github.com/SeanChenR/ghibli.git
cd ghibli
uv sync

# Optional
cp .env.example .env

uv run ghibli         # 第一次啟動會出現 model picker，引導填入 API key
```

兩種設定 credential 的方式，擇一即可：

- **A. 用 picker（推薦給第一次跑的人）**：直接 `uv run ghibli`，沒任何 credential 時 picker 會帶你過 onboarding（選 provider → prompt 貼 API key → 寫到專案目錄的 `.env`），不用事先準備設定檔。
- **B. 自己編 `.env`**：先 `cp .env.example .env`，把對應的 key 填進去再跑 `uv run ghibli`。適合已經知道要用哪個 provider、或想一次設好多個後端切換的情況。

如果要跑 eval：

```bash
uv run python -m evals.run_evals --model gemini-vertex    # 或 gemma4 / gpt51
uv run python -m evals.compare_models                      # 看跨模型 accuracy 比較表
```

---

## Build a Tool

### 架構總覽

```
自然語言輸入
     ↓
cli.py           ← Typer 對話 loop；model 解析 4 層 + welcome banner + tool 即時可視化
     ↓
picker.py        ← 5 選項 provider picker + API Key / Vertex onboarding（寫 .env）
     ↓
agent.py         ← Function Calling loop；分兩條路：Gemini 原生 SDK 或 LiteLLM
     ↓                           ↑
sessions.py      ←→  <cwd>/.ghibli/sessions.db  ← SQLite turn 歷史
     ↓
tools.py         ← 13 個 GitHub tool function（signature + docstring 就是 LLM schema）
     ↓
github_api.py    ← httpx → api.github.com（follow_redirects=True，共用進入點）
     ↓
output.py        ← Rich Markdown / JSON 輸出
```

幾個關鍵決策：

- **無 default 的模型**：model 解析優先序 `--model > .ghibli/last_model > picker`，三層全落空就 `exit 1`，不 fallback 到某個預設模型。
- **多後端路由**：`openai:<slug>` / `ollama:<slug>` / `gemma:<slug>` 走 LiteLLM；無 prefix（如 `gemini-2.5-flash`）走 google-genai SDK。同一組 13 個 tool schema 兩邊共用。
- **Project-local 狀態**：`sessions.db` 與 `last_model` 都放 `<cwd>/.ghibli/`（已加進 `.gitignore`），一個 repo 一套獨立狀態，跨 repo 切換不污染。
- **Function Calling 而非 prompt + JSON**：SDK 自動驗型別、支援多步 agent loop；eval 能直接從 response 讀出 tool 序列判分。

### CLI 使用方式

```bash
uv run ghibli                        # 開新 session（進互動對話）
uv run ghibli --session <id>         # 接續歷史 session
uv run ghibli --list-sessions        # 列出所有 session
uv run ghibli --json                 # 輸出原始 JSON 而非 Rich Markdown
uv run ghibli --model openai:gpt-5   # 當次換 model（不動 last_model）
uv run ghibli --model-picker         # 強制重跑 picker 換 provider
uv run ghibli --version
```

範例 query（進入 prompt 後直接打）：

```
可以幫我看看 Spectra-app 這個 Repo 嗎？跟我說一下最近有什麼樣的更新
```

每次 tool dispatch 前 CLI 會印 `→ search_repositories({"q": "..."})`，使用者能看見推理過程，對「黑箱」LLM 很重要（實際輸出樣子見開頭 [Demo](#ghibli--github-intelligence-bridge) 截圖）。

### 模型與 picker

第一次跑 `ghibli` 會看到：

```
Select a model:
  1) Gemini 2.5 Flash (API Key)
  2) Gemini 2.5 Flash (Vertex AI)
  3) Gemma-4-26b (open-weight, via Gemini API)
  4) OpenAI
  5) Ollama Cloud
Select [1]: 4
Get your key at https://platform.openai.com/api-keys
Paste your OPENAI_API_KEY: ******
Which OpenAI model? [gpt-4o-mini]: gpt-5.1
Saved to .env.
```

- Picker 一律固定顯示 5 個 provider，不依賴環境變數偵測——使用者永遠知道有哪些選項。
- 選了缺 credential 的 provider 會提示使用者輸入必要的信息（API Key 類 prompt 隱藏輸入；Vertex 類指引 `gcloud auth application-default login` + project id）。所有 credential 寫進**專案目錄**的 `.env`，不動 `~/.env`。
- 選完 provider 後 OpenAI / Ollama 還會再問一次 model 名稱（default 從環境變數取），寫入 `<cwd>/.ghibli/last_model` 做下次啟動的記憶。
- **啟動時自動檢查 credential**：不管 model 從哪一層來，缺 API key 時終端機模式會直接 prompt 你補、非 TTY 模式（pipe / CI）會 exit 1 並印缺哪個 env var——不會拖到第一句 query 才炸。

CLI 支援 5 個 provider，eval pipeline 最終挑 3 個跑（見 [Model Selection](#model-selection)）。

### 13 個 GitHub API Tools

LLM 無法對 API Endpoint 發 Requestst，只會他只能決定他要呼叫什麼 Function 和帶什麼參數。所以我請 Claude 幫我研究 GitHub REST API Docs，挑出一般 GitHub 問題最常用的端點，將每個端點包裝成 LLM 可以呼叫的 Function Calling：

- Function 的 **signature + docstring** 就是 LLM 看到的 schema，也就是該 Function 的說明和所需要參數。
- Function 的**實作**會統一由同個 Helper 來做。
- Function Calling loop 模型想呼叫哪個就 dispatch，會把結果回傳塞回 `contents`，交由 LLM 自行判斷還需不需要繼續呼叫 Function，直到輸出純文字。

**跨 repo 搜尋**（`q` 必填，支援 GitHub Search qualifier）：

| Tool | REST 端點 | 說明 |
|---|---|---|
| `search_repositories` | `GET /search/repositories` | 主力；支援 `language:` / `stars:>N` / `license:` / `pushed:` / `created:` / `archived:` / `good-first-issues:` / `in:readme` 等 qualifier |
| `search_code` | `GET /search/code` | 找「哪些 repo 的哪個檔案用到某段程式碼」 |
| `search_users` | `GET /search/users` | 找人或組織 |
| `search_issues` | `GET /search/issues` | 跨 repo 搜 issue / PR |

**單一 repo 查詢**（`owner + repo` 必填）：

| Tool | 說明 |
|---|---|
| `get_repository` | metadata（star / fork / primary language 字串） |
| `get_readme` | base64 decode 的 README 文字（>3000 字截斷） |
| `get_languages` | 完整語言 byte 分布 |
| `list_issues` | 單一 repo 的 issue |
| `list_pull_requests` | 單一 repo 的 PR |
| `list_releases` | Release 清單與發布日期 |
| `list_commits` | Commit 歷史，可帶 `sha` / `author` 過濾 |
| `list_contributors` | 貢獻者排行（依 commit 數） |

**單一使用者查詢**：`get_user`（個人公開資訊、follower 數、公開 repo 數）。

**關鍵取捨**：

- **`search_*` vs `list_*` 嚴格分工**：前者跨 repo、`q` 必填；後者只吃 `owner + repo`。名稱相近但語意差很遠——模型容易搞混，所以在 prompt 中有明確說明與禁止場景。
- **每個 tool 只回該 endpoint 該回的資料，不擅自合併**：`get_repository` 只回 metadata（star / fork / 描述），不順便夾帶 README 全文或完整語言分布——這兩個分別由 `get_readme` 跟 `get_languages` 負責。讓模型按需要呼叫對應 tool，回傳才不會夾帶大量無關內容、害模型抓不到重點。
- **所有 tool 回傳 `dict | list`**：原樣丟給 LLM 摘要，程式層不壓欄位——少一層人為耦合。

### Spec-Driven 開發流程

整個專案用 [Spectra](https://github.com/kaochenlong/spectra-app)（SDD）切成 9 個 change，每個 change 先產出 `proposal.md` + `tasks.md` + `specs/*/spec.md`，再由 Claude Code 逐項實作。每個 change 典型生命週期：

```
/spectra-discuss  →  /spectra-propose  →  /spectra-apply  →  /spectra-archive
   (討論需求)         (Plan Mode 產 artifacts)    (TDD 實作)         (歸檔)
```

歷史 change 完整保留在 `openspec/changes/archive/`。

| # | Change | 內容 |
|---|---|---|
| 1 | `project-scaffold` | pyproject.toml、src layout、`GhibliError` 階層、pytest 80% 覆蓋率門檻 |
| 2 | `session-manager` | SQLite session DB（`sessions` / `turns`、CRUD API） |
| 3 | `github-api-client` | `github_api.execute(tool_name, args)` 單一進入點 |
| 4 | `cli-entry-point` | Typer 對話 loop + flags |
| 5 | `github-tools` | 6 個 Python callable + Gemini Function Calling loop + 雙認證 |
| 6 | `output-formatter` | Rich Markdown、session 歷史載回 `contents` |
| 7 | `eval-framework` | 30 條 `queries.yaml` + `run_evals.py`（第一輪 failure 集） |
| 8 | `multi-model-eval` | Tools 6 → 13、LiteLLM 接 3 個模型、加 `judge.py` / ground truth / `compare_models.py` |
| 9 | `interactive-model-picker` | `picker.py`：5 選項 + `ensure_credentials` onboarding；`<cwd>/.ghibli/` |

> **關於 openspec specs 的狀態**：`openspec/specs/` 裡的 spec 是 Phase 1 產出的，架構與 query schema 在 Phase 2 做了一次大改版（見 [Multi-Model Eval](#multi-model-eval)），那些 spec 已 stale。目前實際架構以 `README.md` + `CLAUDE.md` + `evals/README.md` 為準，spec 同步待後續 Spectra change。

---

## Break & Harden

### Break：發現的失敗模式

我刻意設計 30 條 query 壓測這個工具，涵蓋 6 個情境類別 × 多種失敗模式標籤（細節見 [Data Generation](#data-generation30-條-query-設計)）。實際跑下來觀察到的失敗分三類：

**輸入形態層**（query 本身怎樣難）：

| 模式 | 症狀 | 例子 |
|---|---|---|
| `multilingual` | 非英文 query 讓模型直接用該語言從訓練資料背答案 | 6 種非英語：韓文 `discover-004`、德文 `compare-003`、越南文 `debug_hunt-001`、日文 `track_vuln-002`、泰文 `follow_up-003`、西文 `refuse-004` |
| `ambiguous_input` | 印象模糊、滿是 hedge words，模型要猜使用者真正想問什麼 | `track_vuln-001`（「axios 之前**好像**被惡意攻擊**還是**有漏洞**什麼的**」） |
| `messy_phrasing` | 口語、中英夾雜、長句不分段 | `debug_hunt-002`（「我的 langchain agent 一直 infinite loop，呼叫完 tool 又繼續呼叫同一個」） |
| `outdated_assumption` | 使用者帶錯誤預設來問，把自己的猜測當前提 | `debug_hunt-004`（shadcn 升 tailwind v4 後 dropdown 透明，使用者主動猜「是 z-index 問題嗎？」——其實不是） |
| `typo` | 打錯套件 / repo 名 | `debug_hunt-005`（`gema2` → 正確是 `gemma2`） |

**機制層**（模型要做什麼）：

| 模式 | 症狀 | 例子 |
|---|---|---|
| `qualifier_mapping` | 自然語言 → GitHub 搜尋 qualifier（例如「MIT 授權」要對到精確識別字 `license:mit`、`license:apache-2.0`） | `refuse-001`（「MIT license 的 Rust 系統工具」） |
| `temporal_reasoning` | 時間語意推理（版本範圍、`pushed:` vs `created:`、相對日期） | `track_vuln-003`（「React 18 升到 19 breaking change」要對 v18→v19 區間的 release notes） |

**觀察到的模型異常行為**：

| 模式 | 症狀 | 發現 |
|---|---|---|
| 直接回答 | 完全不呼叫工具就列一串 repo 名 | 早期 Gemini 2.5 Flash 常見 |
| 沒呼叫任何工具 | 一個工具都沒呼叫就直接回答 | Gemini 3 Flash 在某些 `debug_hunt` 題會進入「沒結果就反覆改參數」的迴圈，直到撞上呼叫次數上限 |
| 同參數無限重呼 | 連續 20 次都是 `search_repositories({"q": "drizzle-kit"})` | Gemma4 會一直重複呼叫工具 |
| 工具邊界混淆 | 跨 repo 卻用 `list_issues`（只能查單一 repo）、或單一 repo 卻用 `search_issues` | 早期 GPT 系列常見 |
| 矛盾條件仍先驗證 | 明知 fork 數遠大於 star 數不成立，還是呼叫工具證明結果為空再解釋 | 早期 GPT-4o-mini 常見 |
| 多步驟跳步 | 已有 owner / repo 名就跳過 `get_repository` 直接呼叫 `list_releases` | 多步驟 query 常見 |

### Harden：prompt 與 pipeline 迭代

修復分三層。

**1. System prompt（`src/ghibli/prompt.py`）**：CLI 與 eval 共用同一份，都用當天日期注入 prompt。每條規則都對應一個實際觀察到的 failure：

| Prompt 區塊 | 對應的 failure |
|---|---|
| `Never answer from training data` | 直接從訓練資料答 |
| `Always call tools regardless of query language` | 多語言 query 誘發直答 |
| `Query-pattern → tool mapping` | 工具邊界混淆 / 不知該 call 什麼 |
| `Typo correction and unknown owners` | 打錯字 / 使用者只給 repo 名未給 owner |
| `search_repositories — q is always required` | SDK validation error |
| `Named repos first`（指名 repo 必先 anchor） | multi-step 跳 `get_repository` |
| `Partial refusal` 規則（教模型用基本原理推理為何矛盾，不列舉具體不可能條件） | query 混合可行子問題與矛盾子問題 |

**Prompt 設計原則：prompt 不能偷塞 eval 答案**。具體 repo 名、關鍵字、具體的不可能數字（例如 `star > 500k`、`fork > star × 1000`）都不能寫進 prompt——否則模型只是在做 pattern matching，eval 高分代表「我們把答案餵給它」而不是「模型真的懂」。

對應的做法：教模型「怎麼推理」而不是「拒絕哪些情況」。partial refusal 規則用「兩個條件在定義上互斥就拒絕」這種通用原理表達，不列「archived + commit、star > 500k、…」這種具體清單——這樣模型在 prod 上遇到沒見過的矛盾條件也能正確判斷。

**2. Pipeline 層（`evals/models.py`）**：

- **Retry 覆蓋**：`RateLimitError`（429，解析 "try again in Xs"）、`ServiceUnavailableError`（503）、`Timeout`、`ConnectionError` 都有 exponential backoff（5s / 10s / 20s / 40s / 80s，最多 5 次）。
- **Rejudge 工具（`evals/rejudge.py`）**：改 judge.py 或 ground truth 時不重跑 API——讀 stored `tools_called` + `response_full`，用當前的 judge 重判分秒級完成。這是快速迭代的關鍵 enabler。

**3. Query / Ground-Truth 設計層**：

- **TRAP query**：加「MUST not call tool」類規則後模型會過度保守把正常 query 也拒絕。所以 refuse 類 query 本身 mix「可回答 + 不可行」兩部分（partial refusal），Ground-Truth 要求**正常部分必 call 工具、不可行部分必明確拒絕**，兩者都達成才 pass。
- **Multiset 而非 subsequence**：Ground-Truth 只要求「每個必需工具被 call 次數 ≥ 要求」，**順序不管**。理由：data dependency 自然強制順序（`get_repository` 需要 `search_repositories` 的 owner/repo），硬性 sequence 檢查是 artificial discipline，會把對的答案誤判成錯。

### 仍無法根解的限制

以下失敗類型是 prompt / pipeline 改了也無法根解的，刻意留著作為 irreducible failure floor：

#### 1. GitHub 命名差異（compare-005 代表案例）

三個 model 都在 `compare-005`（比較 Google ADK）失敗。根因不在 LLM planning，而在 GitHub 本身的命名：Google ADK 的實際 repo 名是 **`adk-python`**，不是 `adk`。模型照 query 去 `search_repositories({"q": "adk"})` 或 `get_repository({"owner": "google", "repo": "adk"})` 都拿不到對的結果。這是 source system 的資料長相 vs 使用者心智模型之間的 gap，**prompt 層改不了**——除非建一個「名稱別名表」或接 GitHub 以外的資料源（如官方文件搜尋），但那已超出「純 GitHub-based assistant」的題目範圍。

Trade-off：這類「要補外部知識才解得了」的 query 刻意留著，當作 eval 中的 irreducible failure floor。三個 model 的 Compare 類別分數都掉一題（80% / 60% / 80%）主要就在這裡。

#### 2. 沒有官方 trending endpoint

GitHub REST API 沒有 trending endpoint。ghibli 用 `created:>{近期} sort:stars` 近似「最近很紅」，能找到 OpenClaw 等合理結果，但 star 增速快而 created 時間較早的 repo 會被漏掉。這是 API 本身限制。

#### 3. 矛盾條件判斷依賴 LLM 推理

「fork > star × 1000」這種 query，GitHub API 會照單全收回空結果。ghibli 靠 prompt 規則 + 模型 first-principles 推理識別並拒絕。Eval 中 5 條 refuse 在 Gemini / GPT 能 100% 通過、Gemma 80%——這是統計性保證而非程式保證，引入 reasoning 更弱的模型時會鬆動。

#### 4. 非中英多語言覆蓋稀疏

現行 30 條中每個 category 配一種非中英語言（韓/德/越/日/泰/西），共 6 種。複雜多步驟查詢在這幾種以外的語言（阿拉伯文、印地語等）準確性未驗證。要根解得大幅擴充 eval 資料集，成本 × 判分人力負擔陡增。

#### 5. Judge 是結構級、非語義級

`evals/judge.py` 只判「tool 名與次數」，不判「回應內容是否語義正確」。曾試過加 `required_content_all` / `required_content_any_of` 關鍵字比對但撤回：

- **Keyword matching 脆弱**：同義詞 / 多語言 / 不同表達都可能 false negative
- **冗餘**：模型若 call 對工具拿真實 data，回應自然會 mention 關鍵字
- **測錯東西**：容易變成「測 keyword 模式」而非測 grounding + 答題能力

這是刻意的 scope 取捨——要真正做 content-level 判分需要 LLM-as-judge + 更大的人工 audit 預算。目前靠「tool 序列對 + tool 有真的拿到 data」作 Grounding。

---

## Multi-Model Eval

### Pipeline 概觀

```
evals/
├── queries.yaml          # 30 條 query + ground truth（6 scenario × 5）
├── models.py             # LiteLLM 多後端包裝 + model registry + retry
├── run_evals.py          # Runner（逐題執行 → 寫入 results/<model>.json）
├── judge.py              # Multiset subset 判分 + partial refusal 判分
├── rejudge.py            # 不重跑 API，用 stored result 套新 judge（快速迭代）
├── compare_models.py     # 讀 results/*.json 產 Markdown 跨模型 accuracy 表
├── tool_schema.py        # Re-export ghibli 的 tool schemas（CLI / eval 共用）
└── results/
    ├── gemini-vertex.json
    ├── gemma4.json
    └── gpt51.json
```

完整 pipeline 細節（schema、CLI flag、retry 策略、Ground-Truth audit 原則）集中在 [`evals/README.md`](evals/README.md)。本節聚焦設計決策與 write-up。

### Data Generation：30 條 query 設計

30 題 = **6 scenario category × 5 題**。Category 是「使用者在做什麼」，不是「哪個 failure mode」——失敗模式是另一個正交的 tag 維度（multi-label），用於跨 category 分析。

| Scenario | 意義 |
|---|---|
| `discover` | 發掘陌生工具/repo（沒明確目標靠搜尋找候選） |
| `compare` | 對比 2+ 選項 |
| `debug_hunt` | 找類似 bug / issue —「有人遇過嗎？」 |
| `track_vuln` | 安全事件 / 版本追蹤 |
| `follow_up` | 對已知 repo 深挖 |
| `refuse` | 模型應識別不可行並拒絕（partial refusal：混合可行 + 不可行） |

**Category 設計理由**：早期版本把 `qualifier` / `temporal` / `typo` 這些失敗模式當 primary category 分。Phase 2 重構改為「使用者在做什麼」，因為：

1. 真實 AI-dev 場景不會是「我要測 typo」而是「我要 debug 一個 bug」
2. 失敗模式在 real world 是混雜出現的（一條真實 query 可能同時 messy + 多語言 + 矛盾）
3. 多 label tag 允許 cross-category 統計（例如「所有 `multilingual` tag 的 query 正確率」）

**Failure mode tags（7 個，multi-label）**：

- **輸入形態類**：`multilingual` / `ambiguous_input` / `messy_phrasing` / `outdated_assumption` / `typo`
- **機制類**：`qualifier_mapping` / `temporal_reasoning`

**多語言覆蓋**：每個 category 配一種非中英語言，共 6 種：韓文（`discover-004`）、德文（`compare-003`）、越南文（`debug_hunt-001`）、日文（`track_vuln-002`）、泰文（`follow_up-003`）、西文（`refuse-004`）。原則是「每種語言至少有代表題，測 prompt 的 "always call tools regardless of query language" 規則」。

### Validation Set 怎麼產 + 怎麼 Audit

#### 30 題的取材

**怎麼決定 query 的**：跟 Claude Code 一起 brainstorm — 我提情境，Claude 提案具體 query 措辭，最後我審核 + 寫入 `queries.yaml`。**不是 LLM auto-generate** — auto-generate 既要產 query 又要產 Ground-Truth 會讓 model 對自己的考卷答案有 prior，違背 eval 公平性。**也不是純手工** — pure manual curation 在 30 格裡很容易踩到自己的盲點（同一類 failure mode 重複塞太多、語言分佈失衡）。Co-design 拿到的是兩邊優點：人類負責「真實場景 grounding + 最終把關」，LLM 負責「diversity audit + 措辭多樣化」。

來源是**真實近期實際發生的場景** — 一方面是我比較好做驗證，另一方面是 follow 社群趨勢，所以 query 刻意環繞最近的生態事件與實際會問的問題：

| Scenario | 每題對應的真實事件 / 情境 |
|---|---|
| `discover` | SDD 工具、AI Agent Skills 倉庫、RAG 文件 parser 工具、LLM eval framework（韓文）、Claude Code plugin 生態 |
| `compare` | OpenClaw vs Hermes Agent、Nextjs vs TanStack Start、Prisma vs Drizzle（德文）、bun vs pnpm vs npm、LangChain / LangGraph / Google ADK |
| `debug_hunt` | Next.js hydration mismatch（越南文）、langchain agent infinite loop、prisma → drizzle migration FK 問題、shadcn dropdown 透明（z-index?）、llama.cpp gguf 轉換 typo |
| `track_vuln` | axios 供應鏈攻擊、React 重大漏洞（日文）、React 18 → 19 升級、Python no-GIL free-threading 穩定性、LiteLLM compromise |
| `follow_up` | TanStack contributors / release 節奏、Podman vs Docker 社群活躍度、Kubernetes 最近 release（泰文）、Qdrant 起源語言、Google MCP Toolbox 方向 |
| `refuse` | 混合可行 + 矛盾子問題（partial refusal 測試），例如「找 archived 但最近還有 commit 的 repo」、「2090 年的 JavaScript runtime」 |

這樣設計的好處：reviewer 看到 `track_vuln-001` 問的是真實 axios 事件，而不是 `track_vuln-foo-001 "query about some CVE"`——每題都是**可以實際拿去 CLI 跑而且模型給出答案是有 meaning 的**。

#### 在 30 格裡擠 diversity 的規則

1. **Category 平衡**：6 scenario × 5，避免模型在某類失手但總分仍高的 blind spot
2. **Failure mode multi-label**：每題至少踩 1 個 failure mode tag，同一個 tag 不在同 category 內重複 5 題（例如 `multilingual` 6 個 category 各一條，不是 discover 塞 3 條韓文）
3. **Difficulty 分層**：每個 category 5 題混搭 `easy / medium / hard`，避免全 hard 或全 easy 把 model 分數壓在 floor 或頂在 ceiling
4. **刻意留不可解題**：如 `compare-005`（Google ADK naming gap）、矛盾條件 refuse 類。測的不是「模型會不會答對」，而是「答不對時反應合不合理」（承認不知 vs 幻想答案）

#### Ground-Truth 怎麼 audit

30 題的 `ground_truth` 是我先寫的（「這題應該 call 什麼」）— 但 first-pass Ground-Truth 會有**過度紀律性**的傾向，例如總覺得每題都該先 `get_repository` 當 anchor。Audit 的實際流程：

```
跑 eval → 看 common failure → 判斷是模型問題 or Ground-Truth 太嚴 → 修對應那一側 → rejudge 秒級確認
```

具體例子：

- **Ground-Truth 太嚴格 → 修 Ground-Truth**：debug_hunt 5 題原本 `tool_sequence: [get_repository, search_issues]`。但 `search_issues q='repo:owner/name keyword'` 已經 scope 到特定 repo，前置 `get_repository` 是紀律檢查不是功能必要 — 三個 model 都在這步被判 fail 時，合理的修法是**改 Ground-Truth**而非加 prompt 規則。改成 `[search_issues]` 單工具後，failure 消失也沒遮掉任何真實錯誤。
- **Model 問題 → 改 prompt / pipeline**：multi-step 跳步、矛盾條件仍先驗證 — 這類 failure 證明模型真的沒照使用者預期走，要改的是 prompt 規則（加 `Named repos first`、partial refusal 規則）。
- **都不改，承認 irreducible**：`compare-005` ADK naming gap。GT 是合理的（真的要 3 個 repo 各自 metadata 才能比較），model 能力也沒問題（planning 對的），失敗根因在 GitHub 命名——寫進 [仍無法根解的限制](#仍無法根解的限制)。

**audit 原則**：`tool_sequence` 只列**功能必要**的工具，**紀律性** anchor 不進。若 `list_*` / `get_readme` / `get_languages` 這類工具本身就吃 `owner + repo` 作 input，就不強求前置 `get_repository`。保留 `get_repository × N` 嚴格要求的場景：compare N-way（N 個 repo 各自 metadata）、follow_up deep-dive。

### Ground Truth 設計

每題 `ground_truth` 欄位：

```yaml
# 一般 scenario
ground_truth:
  tool: search_repositories            # 必須出現在 tools_called
  tool_sequence:                       # Multiset：每個工具被 call 次數 ≥ 要求
    - search_repositories
    - get_repository

# Refuse scenario（partial refusal）
ground_truth:
  tool: refuse
  valid_parts_tool_sequence:           # 正常部分必 call 的工具（multiset 判分）
    - search_repositories
  refusal_keywords:                    # 回應必須包含拒絕詞彙（case-insensitive）
    - 無法
    - inherently contradictory
```

**GT 設計原則**：

1. **多步優先**：非 refuse 類 query 若一個工具答不出預期，`tool_sequence` ≥ 2。
2. **單工具足夠也 OK**：`search_issues q='repo:owner/name keyword'` 已 scope 到特定 repo，不需要前置 `get_repository` 當 anchor — 強求是紀律檢查不是必要。debug_hunt / track_vuln 有些題就是 `[search_issues]` 單工具。
3. **Multiset 而非 subsequence**：順序不管，計數要對。理由見 [Harden 第 3 層](#hardenprompt-與-pipeline-迭代)。
4. **Refuse 測 partial refusal**：正常部分必 call 工具、不可行部分必在回應中明確拒絕（關鍵字比對 `flagged_refusal`）。
5. **Prompt 無 eval leakage**：具體 Ground-Truth 細節（repo 名、impossibility 門檻）嚴禁出現在 `src/ghibli/prompt.py`。

### Judge 邏輯

```python
judge(tools_called, response_text, ground_truth) -> dict
```

回傳 `{ tool_match, sequence_match, flagged_refusal, pass_ }`。

- **一般 scenario**：`pass_ = tool_match AND sequence_match`
- **Refuse scenario**：`pass_ = sequence_match(valid_parts) AND flagged_refusal`

### Model Selection

目標：3 個開源、閉源 model 混合，全員 ≥ 85%。

| Nickname | 模型 | 類型 | Provider |
|---|---|---|---|
| `gemini-vertex` | `gemini-3-flash-preview` | **閉源** | Vertex AI（ADC + global endpoint）|
| `gpt51` | `gpt-5.1-2025-11-13` | **閉源** | OpenAI |
| `gemma4` | `gemma-4-26b-a4b-it` | **開源權重** | Gemini API |

**怎麼選的**：

1. **Gemma-4-26b（open-weight 代表）**：Google 新出的 open-weight 模型，透過 Gemini API 存取避開本機資源限制。Free tier 有 RPM 限制但沒 TPM 限制。
2. **Gemini 3 Flash Preview**：原本配的是 Gemini 2.5 Flash。所有 prompt / judge 調整跑完後 2.5 Flash ceiling 76.7%（5 次 run 範圍 26.7–76.7%），上限明顯。換成 `gemini-3-flash-preview`（帶 thinking、tool planning 更穩定）後到 96.7%。要走 Vertex AI 的 global endpoint（preview model 不支援 region endpoint）+ ADC 認證。
3. **GPT-5.1**：代表 OpenAI 的 reasoning model 86.7% 剛好過 threshold。

**刻意不選的（試過、配置過 eval、然後淘汰）**：

| 候選 | 最終分數 | 不選的原因 |
|---|---|---|
| `gemini-2.5-flash` | 13.3% → 76.7% (ceiling) | v2 query 第一次跑 13.3%（同期 GPT 50%、Gemma 73.3%——三個 model 對 v2 反應差距很大）。經完整 prompt + judge 迭代後 2.5 Flash 衝到 76.7% 就上不去 — thinking 能力不足讓 multi-step 推理常 dead-end，ambiguous query 會在 search 卡住。 |
| `gpt-4o-mini` | 70% (21/30，跑 2 次都同分) | 便宜但 tool-selection 邊界混淆，prompt 怎麼調都過不了 85% |
| `gpt-4o` | 73.3% (22/30) | 比 mini 好但仍不到 85%。沒 reasoning 模式可開 |
| `gpt-5-mini` | — | reasoning=medium 預設跑 30 題 90+ 分鐘，等待時間太久 |
| `ollama-cloud qwen3.5:cloud` | — | 單題 60–90 秒，30 題一輪 30–45 分鐘。harden 階段要跑數十次，這個 latency 會直接讓迭代停擺。CLI 留著作 demo 選項 |

**為什麼最終這 3 個能過 85%——映射到淘汰候選缺什麼**：

| 必要條件 | 缺它的候選會發生什麼 |
|---|---|
| Multi-step tool planning（一連串 tool call 不掉鏈） | `gemini-2.5-flash` 在第 3-4 步偶爾 dead-end，ceiling 撞 76.7% |
| Tool selection 紀律（跨 repo / 單 repo 不混用） | `gpt-4o-mini` / `gpt-4o` 卡 70%/73% 主因 |
| Partial refusal 的 first-principles reasoning | 沒 reasoning 能力的模型會卡在「告訴它哪些情況要拒絕」的黑名單 prompt——一加 MUST 就過度保守、不加就 verify 完空集再答 |
| 可以快速 iterate 的 latency | `ollama-cloud` / `gpt-5-mini` 不是分數不行，是時間預算撐不起 30+ 次 rerun |

### 迭代過程：怎麼推到 ≥85%

從一開始三個 model 都 100% 到最後 86.7 / 90 / 96.7，中間經過 query / prompt / judge 三層交替調整。所有歷史 run 在 `evals/results-local/`（不入 git）。

#### Phase 1 — v1 query 太簡單：100% / 100% / 100%

最初 30 題用 5 個失敗模式類別（qualifier / temporal / typo / contradiction / multi_step / tool_selection）切，每題只考一個固定 failure mode，模型只要 prompt 提到對應策略就能背過。

| Model | v1 |
|---|---|
| Gemini 2.5 Flash | 30/30 = **100%** |
| GPT-4o-mini | 30/30 = **100%** |
| Gemma-4-26b | 30/30 = **100%** |

完美分數的 eval 沒有 signal——v1 沒有 break 模型的能力，eval 失去意義。**這就是「query 沒鑒別度」的具體樣子**。

#### Phase 2 — v2 query 改 6 scenario，三模型崩盤

重構成「使用者在做什麼」的 6 scenario × 5 題，把真實 AI-dev 場景塞進去（compare-005 ADK 比較、debug_hunt OpenClaw 報錯、track_vuln axios 供應鏈事件等）+ 多語言 + partial refusal + 多步 qualifier。query 一改完跑下去：

| Model | v2 first run |
|---|---|
| Gemini 2.5 Flash | 4/30 = **13.3%** |
| GPT-5.1 | 15/30 = **50%** |
| Gemma-4-26b | 22/30 = **73.3%** |

三個 model 全部從 100% 跳水。Gemini 差最多；GPT 中位 50%；Gemma 反而韌性最好的（73.3%）但離 threshold 還很遠。新 query 真的有 break 模型的能力——**現在問題是 break 太多，要 harden**。

#### Phase 3 — Prompt 迭代：上推到 70-83%

逐條對應實際 failure 加 prompt 規則：

- `Never answer from training data` 修「直接從訓練資料答」
- `Always call tools regardless of query language` 修多語言誘發直答
- `Query-pattern → tool mapping` 修工具邊界混淆
- `Named repos first` 修 multi-step 跳 `get_repository`
- Partial refusal first-principles reasoning（不列舉具體 impossibility，避免 eval leakage）

| Model | After prompt iteration |
|---|---|
| Gemini 2.5 Flash | 26.7 → 46.7 → 73.3 → **76.7%** (ceiling) |
| GPT-5.1 | 50 → 83.3 → 76.7 → **76.7%** (oscillating) |
| Gemma-4-26b | 73.3 → **83.3** → 80% |

顯著提升但**仍無人穩定過 85%**。

#### Phase 4 — Judge 放寬：subsequence → multiset

審視 GT 失敗例子發現很多是「模型呼叫對的工具但順序不是 Ground-Truth 預期的」——例如 Ground-Truth 寫 `[get_repository, list_releases]`，模型先 list_releases 再 get_repository verify，順序顛倒但功能對。原本 subsequence 判分把這種算錯，是 artificial discipline；data dependency 天然強制順序（get_repository 後才有 owner/repo 給 list_releases 用），不需要再加一層順序檢查。

改成 multiset subset（每個必需工具被 call 次數 ≥ 要求，順序不管）：

| Model | After judge change |
|---|---|
| GPT-5.1 | 76.7 → **86.7%** (26/30) ✓ |
| Gemma-4-26b | 80 → **90%** (27/30) ✓ |
| Gemini 2.5 Flash | 76.7 → 76.7% (23/30) ✗ |

GPT-5.1 / Gemma-4 越線。**Gemini 2.5 Flash 還是過不了**——已經把 prompt 該調的都調了，judge 也放寬到合理上限。我認為是 model 本身的 ceiling。

#### Phase 5 — Gemini 2.5 Flash → 3 Flash preview

2.5 Flash 5 次 run 範圍 26.7–76.7%，76.7% 就是這個 model 的 ceiling。具體缺陷：
- thinking 能力不足，multi-step 推理常出錯
- Tool planning 在 ambiguous query 偶爾 dead-end search

升到 `gemini-3-flash-preview` thinking 能力、tool planning 更穩定：

| Model | After 3 Flash |
|---|---|
| Gemini 3 Flash | **96.7%** (29/30) ✓ |

#### 最終達成：完整軌跡

| Phase | What changed | Gemini | GPT | Gemma |
|---|---|---|---|---|
| v1 簡單 query | 5 cat × 6 題 | 100% | 100% | 100% |
| v2 重構 query | 6 scenario × 5 + 多語言 | 13.3% | 50% | 73.3% |
| Prompt 迭代 | 5 條規則 | 76.7% (ceiling) | ~83% | ~83% |
| Judge multiset | 移除 subsequence | 76.7% ✗ | **86.7%** ✓ | **90%** ✓ |
| Gemini 3 Flash | 換 model | **96.7%** ✓ | 86.7% | 90% |

最終三個 model 全部 ≥85% threshold（細節見下節 [執行與結果](#執行與結果)）。

### 執行與結果

```bash
uv run python -m evals.run_evals --model gemini-vertex      # 結構級判分
uv run python -m evals.deepeval_judge --model gemini-vertex # 語意級判分（疊在上面）
uv run python -m evals.compare_models                        # 跨模型 accuracy 表
```

ghibli 用**兩層判分疊加**：

- **結構級**（`evals/judge.py`）：看「該叫的工具有沒有叫到」——multiset 比對 tool 序列、deterministic、0 LLM cost。是 ≥85% threshold 的判分主體。
- **語意級**（`evals/deepeval_judge.py`）：看「答出來的東西到底對不對」——LLM-as-judge 跑 4 個 metric（answer_relevancy / faithfulness / hallucination / partial_refusal），補結構級看不見「答案內容」的盲點。

#### 4 個 metric 的 prompt 跟 threshold

| Metric | Prompt 從哪來 | Threshold | 設值理由 |
|---|---|---|---|
| `AnswerRelevancyMetric` | DeepEval 內建 | **0.7** | DeepEval 建議的 production 預設值（保守值） |
| `FaithfulnessMetric` | DeepEval 內建 | **0.7** | 同上 |
| `HallucinationMetric` | DeepEval 內建（吃 `tool_calls_detail` 的 `result_preview` 當 ground-truth context，不靠 judge 自己訓練資料） | **0.7** | 同上 |
| `GEval("Partial Refusal Quality")` | **自寫 criteria** | **0.6** | refuse 類判斷主觀（什麼算「明確拒絕」），給寬一點避免過嚴；但不能太低，不然編造也會被判過 |

**3 個 RAG metric 直接用 DeepEval built-in prompt**——這些是 DeepEval 為通用 LLM 應用調過的 judge prompt，包含 verdict 抽取、reasoning chain、self-consistency 等，自己重寫風險高（會弱化 metric 信號）。我們做的是**選對 metric** + **餵對 context**（特別是 hallucination metric 的 retrieval context 改用 tool 結果而非 query 文字），不重做 prompt。

**`GEval` 的 criteria 自己寫**（位置：`evals/deepeval_judge.py`）——因為「partial refusal 品質」是 ghibli 場景特有，DeepEval 沒對應的 built-in：

```python
criteria=(
    "Determine whether the response correctly handled a query mixing "
    "valid and contradictory sub-questions: the valid part should be "
    "answered using actual data, while the contradictory part should "
    "be explicitly refused with a reason — not fabricated or silently ignored."
)
```

GEval 拿到這段描述後會自己構造 evaluation steps、判分 rubric，用 chain-of-thought 推理出 0–1 的分數。**Threshold 跟 criteria 都沒做 per-query 調校**——沒有「semantic ground-truth」可以對齊，0.7/0.6 是經驗值不是 tuned value，這是接受 LLM-as-judge 本身有 ~5–10% 變動的取捨。

#### 跨 Judge 結論（30 題 × 3 model = 90 runs）

| Model | **結構級** | **語意級** | Disagreement |
|---|---|---|---|
| `gemini-3-flash` | **96.7%** (29/30) | **96.7%** (29/30) | 2 |
| `gemma-4-26b` | **90.0%** (27/30) | **90.0%** (27/30) | 6 |
| `gpt-5.1` | **86.7%** (26/30) | **96.7%** (29/30) | 5 |

三個 model 結構級全部過 ≥85% threshold。**Disagreement 是核心 signal**——同題結構 PASS 但語意 FAIL（或反之），總共 13 題揭示了現有 eval 看不到的盲點，具體例子在 [Performance Analysis](#performance-analysis)。

值得一提的是 **gpt-5.1 語意分（96.7%）比結構分（86.7%）高 3 分**——4 題結構倒但語意過，意味著結構級 GT 對 reasoning 強的 model 偏嚴。

#### 結構級 per-category 細項

| Model | Overall | Discover | Compare | Debug Hunt | Track Vuln | Follow Up | Refuse |
|---|---|---|---|---|---|---|---|
| `gemini-3-flash` | **96.7%** | 100% | 80% | 100% | 100% | 100% | 100% |
| `gemma-4-26b` | **90.0%** | 100% | 60% | 100% | 100% | 100% | 80% |
| `gpt-5.1` | **86.7%** | 60% | 80% | 100% | 100% | 80% | 100% |

Compare 類別是共同瓶頸（見 [仍無法根解的限制 §1](#仍無法根解的限制)）。

### Performance Analysis

#### 最終 3 個 model 的初始失敗模式（harden 前）

| Model | 主要失敗模式 | 具體觀察 |
|---|---|---|
| Gemini 3 Flash | 沒結果就反覆改參數 | 搜尋 0 結果時會持續改 query 重試，多數情況最終會自然收斂答出 |
| Gemma-4-26b | 同參數重複呼叫 | 例如連續多次 `search_repositories({"q": "drizzle-kit"})` 同參數，最終會收斂答出但拖慢時間 |
| GPT-5.1 | Reasoning 預算配置 | reasoning=medium 預設 30 題 90+ 分鐘太慢；none 偶爾 under-think |

被淘汰的候選 model 在 harden 階段的失敗模式整理在 [刻意不選的 table](#model-selection)，主要是：Gemini 2.5 Flash thinking 不足撞 76.7% ceiling、GPT-4o-mini / GPT-4o tool-selection 混淆卡 70%/73%、Ollama / GPT-5-mini latency 預算撐不起迭代。

#### Harden 後的差異模式

- **Compare 類（共同瓶頸）**：Gemini 80% / Gemma 60% / GPT 80%。主因是 `compare-005` ADK naming gap（三個都倒，見 [仍無法根解的限制 §1](#仍無法根解的限制)）；Gemma 多倒一題在比較跑 N-way 時漏 `get_repository` 的 anchor。
- **Refuse 類（Gemma 唯一 <100%）**：Gemma 80%。Gemma 在 partial refusal 的 first-principles reasoning 上偶爾把正常 query 也一併拒絕（過度保守）。
- **Discover 類（GPT 唯一 <100%）**：GPT 60%，其他 100%。GPT-5.1 在 discover 的 qualifier mapping 上偶爾不帶足夠 qualifier（例如 `stars:>1000` 忘記加 `pushed:>` 限時），導致結果過舊。

#### 有趣觀察

1. **Gemini 2.5 → 3 Flash 的 26.7%–76.7% → 96.7% 跳躍**：同一個 family 的小版本升級在 tool-use 任務上影響極大。2.5 Flash 在所有 prompt 調整後 ceiling 76.7%，3 Flash preview 直接到 96.7%。差別主要在 thinking 能力——multi-step tool planning 的穩定性是 thinking 能力的直接體現。
2. **Reasoning effort 的甜蜜點**：GPT-5.1 預設 `reasoning=none` 時 86.7%；試過 `reasoning=low` 沒顯著提升但 latency 翻倍；`reasoning=medium` 會在 30+ 題跑出 90 分鐘等級的累積時間。對「知道怎麼做、只是需要穩定執行」的 tool-use eval，reasoning 不是 free lunch。
3. **Open-weight 能打到 90%**：Gemma-4-26b 作為 open-weight 模型做到 90%，超過 GPT-5.1 的 86.7%。這證明 2026 年 open-weight 生態（尤其有 thinking 能力的那批）在結構化 tool-use task 上已經可以跟去年閉源模型比較。

### 跨 Judge Disagreement 細節

[執行與結果](#執行與結果) 那裡已經給了結構級 / 語意級 / disagreement 的總分，這裡展開 13 題 disagreement 的具體模式——這才是語意級 judge 真正補進來的洞察。

#### (a) 結構 PASS、語意 FAIL：模型呼叫對工具但答得不好

| Model | Query | 失敗 metric | 觀察 |
|---|---|---|---|
| `gemini-vertex` | `follow_up-002` | answer_relevancy 0.62 | 工具都對，但答案塞 Qdrant features 沒回到「always Rust? actively maintained? README positioning?」 |
| `gemma-4-26b` | `compare-002` | faithfulness | 工具拿到的 data 跟 response 對不上，模型自己加料 |
| `gemma-4-26b` | `refuse-001` | hallucination | refuse 類但回答時編造 repo |
| `gpt-5.1` | `debug_hunt-002` | hallucination | tool 都呼叫對，response 卻幻想了不存在的細節 |

這類就是現有結構級 eval 的真正盲點——分數不該算 PASS。

#### (b) 結構 FAIL、語意 PASS：GT 太嚴，模型實際答對了

| Model | Query | 觀察 |
|---|---|---|
| `gpt-5.1` | `compare-005`、`discover-001`、`discover-003`、`follow_up-002` | 結構 GT 列了某些工具，模型用稍微不同組合也答對；語意 judge 看內容認為 OK |
| `gemma-4-26b` | `compare-004`、`compare-005`、`refuse-003` | 同上 |

這類**反向告訴我們 GT 還可以再放寬**——`get_repository` 的紀律性 anchor 對 reasoning 強的模型可能不必要。

#### 語意級判分的限制

- **gemini-vertex / gemma4 結構分跟語意分一樣**（29 / 27）——巧合不是相關，因為 disagreement 兩端互相抵消（structural_only ≈ semantic_only）
- **Judge 自己有 bias**：用 Gemini 2.5 Flash 當 judge，遇到 CVE / vulnerability 內容會被 safety filter 攔（gpt51 那次有 1 個 metric 回 None），靠 `ignore_errors=True` 忽略個別失敗 metric
- **結果僅一次跑分**：LLM-as-judge 非 deterministic，cache 開了但同題重跑分數仍會 ~5–10% 變動

### Synthesizer 自動生題的對照實驗

順便試了 DeepEval 的 `Synthesizer.generate_goldens_from_scratch` 自動生 15 條 query 跟手動 30 題對比（細節在 [`evals/synthesized-queries/findings.md`](evals/synthesized-queries/findings.md)）。結論：

| 維度 | Synthesizer 自動生題 | 手動 + Claude Code co-design |
|---|---|---|
| GitHub scope 符合度 | ~53%（一半題目偏離成 essay 題如 "Deduce Google's strategic priorities"） | 100% 都能 map 到 13 個 tool |
| 多語言覆蓋 | 0/15（全英文） | 6 種非英語（韓/德/越/日/泰/西）|
| eval-leakage 風險 | 高（同 LLM 生 query + 生 expected_output + 當 judge）| 低（人類負責 grounding） |
| 引用真實 GitHub 路徑 | 失準（`ms/vscode` 不是真實路徑） | 對齊真實事件（axios 供應鏈、React 漏洞等） |

**結論**：自動生題對 NL→tool-call 場景**不能取代手動 curation**，但作為對照實驗確認了我們的 query 設計策略是對的。詳細 review 見 findings.md。

---

## 單元測試 & 整合測試 ( 基於 Test Driven Development; TDD )

184 條測試（183 unit + 1 integration）、整體覆蓋率 87%，`pyproject.toml` 強制 `--cov-fail-under=80` 門檻。單元測試 mock 外部依賴（`litellm.completion`、`genai.Client`、`httpx`、SQLite、`typer.prompt`）；整合測試用 `@pytest.mark.integration` 真打外部 API。

```bash
uv run pytest                           # 預設全跑
uv run pytest -m "not integration"      # 只跑 unit（CI 無外網依賴）
uv run pytest tests/integration/        # 只跑整合測試
```

**為什麼停在 87% 而非 100%**：剩下的 ~13% 主要在（1）連線 / rate limit / timeout 錯誤分支——mock `RateLimitError` + 偽造 Retry-After 寫起來腐爛快、回報低；（2）SQLite early return（`if row is None: return None`）；（3）13 個 tool wrapper 的轉發層，結構一致、頭尾範本已保證其餘。業界共識 80% 是 sweet spot，心力花在 eval 30 條 ground truth 上比追 100% 覆蓋率更實際。

## 開發指令

```bash
uv run ghibli                      # CLI 對話
uv run pytest                      # 測試（含 80% 覆蓋率門檻）
uv run python -m evals.run_evals --model <name>          # 跑 eval
uv run python -m evals.run_evals --model <name> --query-ids 'compare-005'  # 針對特定題
uv run python -m evals.rejudge --model <name>            # 不重跑 API 重判分
uv run python -m evals.compare_models                    # 跨模型 accuracy 表
uv run ruff check src/
```
