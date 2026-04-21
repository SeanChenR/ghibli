## 1. 測試 — 單元測試（Red，使用 mock）

- [ ] 1.1 在 `tests/unit/test_intent.py` 寫 `test_github_intent_is_immutable()` — 建立 `GitHubIntent` 實例後嘗試賦值任一欄位，斷言 raise `dataclasses.FrozenInstanceError`；寫 `test_github_intent_fields_accessible()` — 建立實例後斷言四個欄位值正確（對應：GitHubIntent dataclass defines the stable output schema）
- [ ] 1.2 [P] 在 `tests/unit/test_intent.py` 寫認證模式測試（authentication resolved from environment at call time，使用 `monkeypatch`）：
  - `test_api_key_mode_used_when_gemini_api_key_set()` — 設定 `GEMINI_API_KEY=fake`、清除 `VERTEX_PROJECT`，mock `genai.Client`，斷言以 `api_key="fake"` 建立 client（對應：API key mode used when GEMINI_API_KEY is set）
  - `test_vertex_ai_mode_used_when_vertex_project_set()` — 清除 `GEMINI_API_KEY`、設定 `VERTEX_PROJECT=my-proj`，mock `genai.Client`，斷言以 `vertexai=True, project="my-proj"` 建立 client（對應：Vertex AI mode used when VERTEX_PROJECT is set）
  - `test_api_key_takes_precedence_over_vertex()` — 同時設定兩個變數，斷言使用 API key 模式（對應：GEMINI_API_KEY takes precedence over VERTEX_PROJECT）
  - `test_vertex_location_defaults_to_us_central1()` — 設定 `VERTEX_PROJECT` 但不設定 `VERTEX_LOCATION`，斷言 `location="us-central1"`（對應：Vertex AI mode defaults location to us-central1）
  - `test_vertex_location_used_when_set()` — 設定 `VERTEX_LOCATION=asia-east1`，斷言 client 使用此 location（對應：Vertex AI mode uses VERTEX_LOCATION when set）
  - `test_no_auth_raises_intent_parse_error()` — 清除 `GEMINI_API_KEY` 和 `VERTEX_PROJECT`，斷言 raise `IntentParseError` 含訊息 `"No Gemini auth configured"`（對應：no auth configured raises IntentParseError）
- [ ] 1.3 [P] 在 `tests/unit/test_intent.py` 使用 `unittest.mock.patch` mock `google.genai.GenerativeModel.generate_content`：寫 `test_parse_intent_returns_github_intent()` — mock 回傳有效 JSON `{"endpoint":"/search/repositories","method":"GET","params":{"q":"python"},"description":"search"}` 並斷言回傳值為 `GitHubIntent` 實例（對應：parse_intent converts natural language to GitHubIntent）
- [ ] 1.4 [P] 在 `tests/unit/test_intent.py` 寫 `test_invalid_json_response_raises_intent_parse_error()` — mock Gemini 回傳無效 JSON，斷言 raise `IntentParseError`；寫 `test_missing_fields_in_response_raises_intent_parse_error()` — mock 回傳缺少 `"endpoint"` 欄位的 JSON，斷言 raise `IntentParseError`（對應：unparseable intent raises IntentParseError）

## 2. 實作（Green）

- [ ] 2.1 在 `src/ghibli/intent.py` 定義 `@dataclass(frozen=True) class GitHubIntent`：欄位為 `endpoint: str`、`method: str`、`params: dict[str, str]`、`description: str`；使用 `field(default_factory=dict)` 讓 params 預設為空 dict（對應：GitHubIntent dataclass defines the stable output schema）
- [ ] 2.2 在 `src/ghibli/intent.py` 實作認證邏輯：在 `parse_intent()` 函式開頭，以下列優先順序建立 `genai.Client`：
  1. 若 `os.environ.get("GEMINI_API_KEY")` 非 None → `client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])`
  2. 否則若 `os.environ.get("VERTEX_PROJECT")` 非 None → `client = genai.Client(vertexai=True, project=os.environ["VERTEX_PROJECT"], location=os.environ.get("VERTEX_LOCATION", "us-central1"))`
  3. 否則 → `raise IntentParseError("No Gemini auth configured: set GEMINI_API_KEY or VERTEX_PROJECT")`
  接著使用 `client.models.generate_content(model="gemini-2.5-flash", ...)` 發送請求（對應：authentication resolved from environment at call time、parse_intent converts natural language to GitHubIntent）
- [ ] 2.3 在 `parse_intent()` 中建立 system prompt，要求 Gemini 以 JSON 格式回傳 `{"endpoint": "...", "method": "...", "params": {...}, "description": "..."}`，呼叫時設定 `generation_config={"response_mime_type": "application/json"}`；以 `json.loads()` 解析回應文字，缺少任何必要欄位或 json 解析失敗時 raise `IntentParseError(f"Failed to parse intent for query: {query}")`（對應：Gemini API uses JSON-mode structured output、unparseable intent raises IntentParseError）
- [ ] 2.4 執行 `pytest tests/unit/test_intent.py -v` 直到所有單元測試通過

## 3. 整合測試（需要真實認證）

- [ ] 3.1 在 `tests/integration/test_intent_integration.py` 寫 `test_parse_intent_search_repos()` — 以 `pytest.mark.skipif(not (os.environ.get("GEMINI_API_KEY") or os.environ.get("VERTEX_PROJECT")), reason="No Gemini auth configured")` 守衛，呼叫真實 `parse_intent("find the most starred Python repositories")`，斷言回傳值是 `GitHubIntent`，`endpoint` 含 `/search`，`method` 為 `"GET"`（對應：common search query is parsed correctly）
- [ ] 3.2 在 `tests/integration/test_intent_integration.py` 寫 `test_parse_intent_invalid_query_raises()` — 使用相同守衛，呼叫 `parse_intent("what is the weather in Tokyo")`，斷言 raise `IntentParseError`（對應：non-GitHub query raises IntentParseError）

## 4. 驗證

- [ ] 4.1 執行 `pytest tests/unit/test_intent.py tests/integration/test_intent_integration.py -v` 確認所有測試通過
- [ ] 4.2 執行 `ruff check src/ghibli/intent.py` 確認無 lint 錯誤
