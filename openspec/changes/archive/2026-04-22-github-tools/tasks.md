## 1. 測試（Red — 先寫，全部應失敗）

- [x] 1.1 [P] 在 `tests/unit/test_tools.py` 寫 `test_all_six_tools_importable()` — `from ghibli.tools import search_repositories, get_repository, list_issues, list_pull_requests, get_user, list_releases`，斷言全部非 None（對應：all 6 functions are importable from tools module）
- [x] 1.2 [P] 在 `tests/unit/test_tools.py` 寫 `test_search_repositories_calls_execute()` — mock `ghibli.tools.github_api.execute`，呼叫 `search_repositories(q="python", sort="stars")`，斷言 mock 以 `("search_repositories", {...})` 被呼叫（對應：search_repositories calls execute with correct tool_name）
- [x] 1.3 [P] 在 `tests/unit/test_tools.py` 寫 `test_get_repository_calls_execute()` — mock `execute`，呼叫 `get_repository(owner="torvalds", repo="linux")`，斷言 mock 以 `("get_repository", {"owner": "torvalds", "repo": "linux"})` 被呼叫（對應：get_repository calls execute with owner and repo）
- [x] 1.4 [P] 在 `tests/unit/test_agent.py` 寫 `test_missing_credentials_raises_tool_call_error()` — 清除 `GEMINI_API_KEY` 與 `VERTEX_PROJECT`，呼叫 `chat("hello", "s1", False)`，斷言 raise `ToolCallError` 且訊息含 `"GEMINI_API_KEY"` 與 `"VERTEX_PROJECT"`（對應：missing authentication raises ToolCallError at chat() call time）
- [x] 1.5 [P] 在 `tests/unit/test_agent.py` 寫 `test_api_key_mode_initializes_client()` — mock `google.genai.Client`，設定 `GEMINI_API_KEY="test_key"`，呼叫 `chat("hello", "s1", False)`（mock generate_content 回傳純文字），斷言 Client 以 `api_key="test_key"` 初始化（對應：GEMINI_API_KEY present uses API Key client）
- [x] 1.6 [P] 在 `tests/unit/test_agent.py` 寫 `test_vertex_mode_initializes_client()` — mock `google.genai.Client`，清除 `GEMINI_API_KEY`，設定 `VERTEX_PROJECT="my-project"`，呼叫 `chat("hello", "s1", False)`，斷言 Client 以 `vertexai=True, project="my-project"` 初始化（對應：VERTEX_PROJECT present uses Vertex AI client）
- [x] 1.7 [P] 在 `tests/unit/test_agent.py` 寫 `test_no_tool_call_returns_text()` — mock `google.genai.Client`，讓 `generate_content` 回傳只有 text part 的 response（無 function_calls），呼叫 `chat("hello", "s1", False)`，斷言回傳值為 mock 的 text 字串（對應：single-turn response with no tool call）
- [x] 1.8 [P] 在 `tests/unit/test_agent.py` 寫 `test_function_calling_loop_executes_tool()` — mock `google.genai.Client`，讓第一次 `generate_content` 回傳含 `function_call` 的 response（tool: `search_repositories`，args: `{"q": "python"}`），第二次回傳純文字；mock `ghibli.agent.tools.search_repositories` 回傳 `{"items": []}`；呼叫 `chat("search python", "s1", False)`；斷言 `search_repositories` 被呼叫一次，且最終回傳文字字串（對應：query triggers one tool call）

## 2. 實作（Green）

- [x] 2.1 在 `src/ghibli/tools.py` 實作 6 個工具函式：每個函式接受對應的關鍵字參數，函式本體呼叫 `github_api.execute(tool_name, {k: v for k, v in locals().items() if v is not None})`；每個函式需有清晰的 docstring 描述功能（Gemini 使用 docstring 決定是否呼叫）（對應：six GitHub tool functions defined in tools.py）
- [x] 2.2 在 `src/ghibli/agent.py` 實作 `chat()` 函式前半段：讀取環境變數 `GEMINI_API_KEY` 與 `VERTEX_PROJECT`；若兩者皆未設定，raise `ToolCallError("Gemini authentication not configured: set GEMINI_API_KEY or VERTEX_PROJECT")`；若 `GEMINI_API_KEY` 已設定，初始化 `client = google.genai.Client(api_key=api_key)`（對應：Gemini client initialized with API Key when GEMINI_API_KEY is set）；否則初始化 `client = google.genai.Client(vertexai=True, project=project, location=os.environ.get("VERTEX_LOCATION", "us-central1"))`（對應：Gemini client initialized with Vertex AI when GEMINI_API_KEY is absent）
- [x] 2.3 在 `src/ghibli/agent.py` 實作 `chat()` 函式後半段：建立 `contents = [{"role": "user", "parts": [{"text": user_message}]}]`；進入 loop，呼叫 `client.models.generate_content(model="gemini-2.5-flash", contents=contents, tools=[search_repositories, get_repository, list_issues, list_pull_requests, get_user, list_releases])`；若 response 有 `function_calls`，遍歷每個 function call，以 try/except 呼叫 `getattr(tools, fc.name)(**fc.args)`，捕捉任何例外並 raise `ToolCallError(f"{fc.name} failed: {e}")`；收集所有 tool results 加入 `contents`（`tool` role），繼續 loop；若 response 只有 text，return `response.text`（對應：chat function executes Gemini Function Calling loop、ToolCallError raised when tool execution fails）

## 3. 驗證

- [x] 3.1 執行 `pytest tests/unit/test_tools.py tests/unit/test_agent.py -v` 確認全部測試通過（Green）
- [x] 3.2 執行 `ruff check src/ghibli/tools.py src/ghibli/agent.py` 確認無 lint 錯誤
