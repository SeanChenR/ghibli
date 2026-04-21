## 1. 測試 — 單元測試（Red，使用 httpx mock）

- [x] 1.1 [P] 在 `tests/unit/test_github_api.py` 加入 `unittest.mock.patch("httpx.request")` 的測試基礎設施；寫 `test_search_repositories_returns_parsed_dict()` — mock httpx.request 回傳 200 含 JSON body `{"total_count": 1, "items": []}`，呼叫 `execute("search_repositories", {"q": "python"})` 斷言回傳值為 dict（對應：execute function accepts tool_name and args and returns parsed JSON、search_repositories returns parsed dict）
- [x] 1.2 [P] 在 `tests/unit/test_github_api.py` 寫 `test_get_repository_substitutes_path_params()` — mock httpx.request，呼叫 `execute("get_repository", {"owner": "torvalds", "repo": "linux"})`，斷言 mock 被以 URL `"https://api.github.com/repos/torvalds/linux"` 呼叫且 params 不含 `owner` 或 `repo` key（對應：get_repository substitutes path parameters）
- [x] 1.3 [P] 在 `tests/unit/test_github_api.py` 寫 `test_unknown_tool_raises_tool_call_error()` — 呼叫 `execute("delete_everything", {})`，斷言 raise `ToolCallError` 且訊息含 `"delete_everything"`（對應：unknown tool_name raises ToolCallError）
- [x] 1.4 [P] 在 `tests/unit/test_github_api.py` 寫 `test_token_adds_authorization_header()` — monkeypatch `os.environ["GITHUB_TOKEN"] = "test_token"`，mock httpx.request，斷言 call kwargs 中 headers 含 `"Authorization": "Bearer test_token"`；寫 `test_no_token_no_auth_header()` — 清除 GITHUB_TOKEN，斷言 headers 不含 Authorization key（對應：GITHUB_TOKEN used for authentication when available）
- [x] 1.5 [P] 在 `tests/unit/test_github_api.py` 寫 `test_user_agent_always_present()` — mock httpx.request，斷言 call kwargs 中 headers 含 `"User-Agent": "ghibli/0.1.0"`（對應：User-Agent header always set）
- [x] 1.6 [P] 在 `tests/unit/test_github_api.py` 寫 `test_404_raises_github_api_error()` — mock httpx.request 回傳 status 404，斷言 raise `GitHubAPIError` 且 `error.status_code == 404`；寫 `test_500_raises_github_api_error()` — mock 回傳 500，斷言同上（對應：HTTP 4xx and 5xx responses raise GitHubAPIError）
- [x] 1.7 [P] 在 `tests/unit/test_github_api.py` 寫 `test_timeout_raises_github_api_error()` — mock httpx.request 側效應為 raise `httpx.TimeoutException("timed out")`，斷言 raise `GitHubAPIError` 且訊息含 `"timeout"`（對應：request timeout set to 10 seconds）

## 2. 實作（Green）

- [x] 2.1 在 `src/ghibli/github_api.py` 定義 `_TOOL_MAP: dict[str, tuple[str, str]]`，映射 6 個工具名稱到 `(method, endpoint_template)` tuple：`search_repositories → ("GET", "/search/repositories")`、`get_repository → ("GET", "/repos/{owner}/{repo}")`、`list_issues → ("GET", "/repos/{owner}/{repo}/issues")`、`list_pull_requests → ("GET", "/repos/{owner}/{repo}/pulls")`、`get_user → ("GET", "/users/{username}")`、`list_releases → ("GET", "/repos/{owner}/{repo}/releases")`（對應：execute function accepts tool_name and args）
- [x] 2.2 在 `src/ghibli/github_api.py` 實作 `execute(tool_name: str, args: dict) -> dict | list`：若 `tool_name not in _TOOL_MAP`，raise `ToolCallError(f"Unknown tool: {tool_name}")`；從 `_TOOL_MAP` 取得 method 與 endpoint_template；從 endpoint_template 抽出路徑參數名稱（以 `{...}` 格式），從 `args` 中 pop 出路徑參數值並填入 endpoint；剩餘 `args` 作為 query params；固定加入 headers `{"User-Agent": "ghibli/0.1.0", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}`（對應：execute function accepts tool_name and args、unknown tool_name raises ToolCallError）
- [x] 2.3 在 `execute()` 中讀取 `token = os.environ.get("GITHUB_TOKEN")`，若非 None 則在 headers 加入 `"Authorization": f"Bearer {token}"`（對應：GITHUB_TOKEN used for authentication when available）
- [x] 2.4 在 `execute()` 中以 `httpx.request(method, url, params=query_params, headers=headers, timeout=10.0)` 發送請求；捕捉 `httpx.HTTPStatusError`，重新 raise 為 `GitHubAPIError(str(e), status_code=e.response.status_code)`；捕捉 `httpx.TimeoutException`，重新 raise 為 `GitHubAPIError("GitHub API request timeout", status_code=408)`；成功時回傳 `response.json()`（對應：HTTP 4xx and 5xx responses raise GitHubAPIError、request timeout set to 10 seconds）

## 3. 整合測試（需要網路連線）

- [x] 3.1 在 `tests/integration/test_github_api_integration.py` 寫 `test_search_repositories_live()` — 以 `pytest.mark.integration` 標記，呼叫 `execute("search_repositories", {"q": "python", "per_page": 3})`，斷言回傳 dict 含 `"items"` key 且 `len(result["items"]) == 3`（對應：search_repositories returns parsed dict）

## 4. 驗證

- [x] 4.1 執行 `pytest tests/unit/test_github_api.py -v` 確認所有單元測試通過
- [x] 4.2 執行 `ruff check src/ghibli/github_api.py` 確認無 lint 錯誤
