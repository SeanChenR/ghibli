# GitHub REST API 能力整理

## 核心 Endpoints（ghibli 已實作）

| Tool | Endpoint | 說明 |
|------|----------|------|
| `search_repositories` | `GET /search/repositories` | 全文搜尋 + 條件篩選 |
| `get_repository` | `GET /repos/{owner}/{repo}` | 單一 repo 完整資訊 |
| `list_issues` | `GET /repos/{owner}/{repo}/issues` | Issues 列表 |
| `list_pull_requests` | `GET /repos/{owner}/{repo}/pulls` | PR 列表 |
| `list_releases` | `GET /repos/{owner}/{repo}/releases` | Release 列表 |
| `get_user` | `GET /users/{username}` | 使用者/組織資訊 |

---

## Search Repositories 完整 Qualifier 系統

`q` 參數支援複雜的 boolean 查詢，以下是實際可用的 qualifier：

### 基本篩選

```
stars:>N            star 數大於 N
stars:N..M          star 數在 N 到 M 之間
forks:>N            fork 數大於 N
size:>N             repo 大小（KB）大於 N
```

### 時間 Qualifier

```
created:>YYYY-MM-DD    建立日期在此之後
created:<YYYY-MM-DD    建立日期在此之前
created:YYYY-01-01..YYYY-12-31    建立日期區間
pushed:>YYYY-MM-DD     最後 push 在此之後（代表仍活躍）
pushed:<YYYY-MM-DD     最後 push 在此之前（可能已廢棄）
```

### 語言與授權

```
language:python        主要語言為 Python
license:mit            MIT 授權
license:apache-2.0     Apache 2.0 授權
license:gpl-3.0        GPL 3.0 授權
```

### 特殊狀態 Qualifier

```
archived:true          已封存的 repo
archived:false         仍在維護的 repo（非封存）
is:public              公開 repo
is:private             私有 repo（需認證）
template:true          可作為 template 的 repo
mirror:true            Mirror repo
```

### 社群友善度

```
good-first-issues:>N   有超過 N 個 good first issue
help-wanted-issues:>N  有超過 N 個 help wanted issue
```

### 文字搜尋位置

```
in:name               搜尋 repo 名稱
in:description        搜尋 description
in:readme             搜尋 README 內容
in:topics             搜尋 topics 標籤
```

### 排序

```
sort=stars            依 star 數排序（預設 desc）
sort=forks            依 fork 數排序
sort=updated          依最後更新排序
sort=help-wanted-issues   依 help-wanted issue 數排序
order=asc/desc        排序方向
```

### 進階組合範例

```
# 2025 年新興 AI 工具
q="created:>2025-01-01 stars:>500 AI"

# 適合貢獻的 Python 入門專案
q="good-first-issues:>10 language:python stars:>1000"

# 仍活躍的 MIT 授權 TypeScript 專案
q="language:typescript license:mit pushed:>2024-01-01 stars:>5000 archived:false"

# README 中提到 machine learning 的新專案
q="machine learning in:readme created:>2024-06-01 stars:>100"

# 可以用作模板的 web 框架
q="template:true stars:>1000 language:python"
```

---

## Rate Limits

| 認證方式 | 每小時限制 |
|---------|----------|
| 無認證 | 60 req/hr |
| Personal Access Token | 5,000 req/hr |
| GitHub App | 15,000 req/hr |

設定方式：`.env` 加入 `GITHUB_TOKEN=<PAT>`

---

## 已知限制與邊界條件

1. **Search API 最多回傳 1000 筆**（每頁 30，最多 34 頁）
2. **無 trending endpoint** — GitHub 沒有官方 trending API，需用 `created:>DATE stars:>N` 近似
3. **Star 上限** — 截至 2026 年，沒有任何 public repo 超過 500,000 stars
4. **Fork/Star 比例** — Fork 數通常是 Star 數的 5–20%，Fork 遠大於 Star 在現實中不存在
5. **未來日期** — `created:>2090-01-01` 會返回空結果
6. **Search 結果排序** — 預設是 best-match 而非 stars，需明確指定 `sort=stars`

---

## Eval 設計依據

`evals/queries.yaml` 的 5 個 category 對應以上能力：

| Category | 測試重點 |
|----------|---------|
| `qualifier` | 特殊 qualifier（license, archived, good-first-issues, template, in:readme） |
| `temporal` | 日期 qualifier（created, pushed, 年份區間） |
| `typo` | 拼寫錯誤容錯與自動修正 |
| `contradiction` | 邊界條件（star 上限、fork/star 比例、未來日期） |
| `multi_step` | 跨 tool 多步驟鏈式操作 |
