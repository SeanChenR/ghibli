# gemini-function-calling Specification

## Purpose

TBD - created by archiving change 'github-tools'. Update Purpose after archive.

## Requirements

### Requirement: chat function executes Gemini Function Calling loop

The function `chat(user_message: str, session_id: str, json_output: bool) -> str` in `src/ghibli/agent.py` SHALL:
1. Create a `google.genai.Client` (see `gemini-authentication` spec for how)
2. Call `client.models.generate_content(model="gemini-2.5-flash", contents=[...], tools=[...])` with the 6 GitHub tool functions
3. If the response contains `function_calls`, execute each tool call via `tools.<function_name>(**args)` and feed the results back to Gemini
4. Repeat step 3 until the response contains only a `text` part (no more function calls)
5. Return the final text response as a Python string

The `session_id` and `json_output` parameters are accepted for future integration with `session-manager` and `output-formatter` but are not required to affect behavior in this change.

#### Scenario: Single-turn response with no tool call

- **WHEN** `chat("Hello, what can you help me with?", "s1", False)` is called
- **THEN** the function returns a non-empty string without calling any GitHub API tool

#### Scenario: Query triggers one tool call

- **WHEN** `chat("Show me the top Python repos", "s1", False)` is called and Gemini decides to call `search_repositories`
- **THEN** `search_repositories` is called with Gemini's arguments, the result is fed back to Gemini, and the final text response is returned

#### Scenario: Query triggers multiple sequential tool calls

- **WHEN** Gemini responds with multiple `function_calls` in a single response
- **THEN** all tool calls are executed, results are collected, and fed back to Gemini in a single `tool` turn before the next `generate_content` call


<!-- @trace
source: github-tools
updated: 2026-04-22
code:
  - src/ghibli/exceptions.py
  - src/ghibli/output.py
  - tests/integration/__init__.py
  - src/ghibli/agent.py
  - src/ghibli/__init__.py
  - tests/__init__.py
  - src/ghibli/cli.py
  - tests/unit/__init__.py
  - pyproject.toml
  - src/ghibli/sessions.py
  - src/ghibli/github_api.py
  - .env.example
  - .spectra.yaml
  - specs/roadmap.md
  - tests/conftest.py
  - CLAUDE.md
  - skills-lock.json
  - src/ghibli/tools.py
  - specs/mission.md
  - uv.lock
  - specs/tech-stack.md
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_tools.py
  - tests/unit/test_github_api.py
  - tests/unit/test_sessions.py
  - tests/unit/test_agent.py
  - tests/integration/test_github_api_integration.py
  - tests/unit/test_cli.py
-->

---
### Requirement: ToolCallError raised when tool execution fails

If a tool function raises any exception during the Function Calling loop, the `chat` function SHALL raise `ToolCallError` with a message identifying which tool failed and the original error message.

#### Scenario: GitHubAPIError during tool call becomes ToolCallError

- **WHEN** `search_repositories` raises `GitHubAPIError` during a Function Calling turn
- **THEN** `chat()` raises `ToolCallError` with a message containing `"search_repositories"` and the original error

<!-- @trace
source: github-tools
updated: 2026-04-22
code:
  - src/ghibli/exceptions.py
  - src/ghibli/output.py
  - tests/integration/__init__.py
  - src/ghibli/agent.py
  - src/ghibli/__init__.py
  - tests/__init__.py
  - src/ghibli/cli.py
  - tests/unit/__init__.py
  - pyproject.toml
  - src/ghibli/sessions.py
  - src/ghibli/github_api.py
  - .env.example
  - .spectra.yaml
  - specs/roadmap.md
  - tests/conftest.py
  - CLAUDE.md
  - skills-lock.json
  - src/ghibli/tools.py
  - specs/mission.md
  - uv.lock
  - specs/tech-stack.md
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_tools.py
  - tests/unit/test_github_api.py
  - tests/unit/test_sessions.py
  - tests/unit/test_agent.py
  - tests/integration/test_github_api_integration.py
  - tests/unit/test_cli.py
-->

---
### Requirement: on_tool_call callback invoked per tool dispatch

The function `chat()` in `src/ghibli/agent.py` SHALL accept a keyword-only parameter `on_tool_call: Callable[[str, dict], None] | None = None`. When this parameter is not `None`, the callback SHALL be invoked exactly once for each tool dispatch, immediately BEFORE the tool function is executed. The callback receives the tool name as its first positional argument and the tool argument dictionary as its second positional argument. Any exception raised inside the callback SHALL be caught inside `chat()` and SHALL NOT propagate: the callback failure SHALL NOT interrupt the function-calling loop, and the message SHALL be logged to stderr so operators can diagnose UI bugs without losing the chat session.

When `on_tool_call` is `None` (the default), `chat()` SHALL behave exactly as it did before this change: no callback invocation and no added overhead. The behavior applies to both the Gemini native SDK path and the LiteLLM path (`openai:`, `ollama:`, `gemini:` prefixes).

#### Scenario: Callback invoked once per tool call in dispatch order

- **WHEN** `chat(query, session_id, False, on_tool_call=cb)` runs a turn in which the agent dispatches `search_repositories`, then `get_repository`, then `get_readme`
- **THEN** `cb` is invoked 3 times with `cb("search_repositories", {...})`, `cb("get_repository", {...})`, `cb("get_readme", {...})` in that order

#### Scenario: Default None keeps legacy behavior

- **WHEN** `chat(query, session_id, False)` is called without `on_tool_call`
- **THEN** the function returns the final text response and does not attempt to invoke any callback

#### Scenario: Callback exception does not break the loop

- **WHEN** `on_tool_call=cb` is provided where `cb(...)` raises `RuntimeError("boom")` on every call
- **THEN** `chat()` still dispatches the tool, feeds the result back to the agent, and returns the final text response normally; `"boom"` is written to stderr


<!-- @trace
source: interactive-model-picker
updated: 2026-04-24
code:
  - src/ghibli/sessions.py
  - README.md
  - .env.example
  - CLAUDE.md
  - src/ghibli/cli.py
  - src/ghibli/picker.py
  - src/ghibli/agent.py
  - evals/models.py
tests:
  - tests/unit/test_agent.py
  - tests/unit/test_cli.py
  - tests/unit/test_picker.py
  - tests/unit/test_sessions.py
-->

---
### Requirement: gemini: prefix routes chat to LiteLLM with Gemini provider

When the resolved model identifier (from the `model` kwarg, `GHIBLI_MODEL` env var, or the default `gemini-2.5-flash`) starts with the literal prefix `gemini:`, `chat()` SHALL route to `litellm.completion(...)` with the model id constructed as `gemini/<slug>` (where `<slug>` is everything after `gemini:`) and `api_key` read from `GEMINI_API_KEY`. The routing SHALL NOT set any `api_base`. This routing is symmetric with the existing `openai:` and `ollama:` prefixes and is the intended path for Gemma model variants served through the Gemini API.

Bare model identifiers that do NOT start with `gemini:`, `openai:`, or `ollama:` SHALL continue to use the native `google.genai.Client` SDK path as defined in the existing `gemini-authentication` spec.

#### Scenario: gemini:gemma-4-26b-a4b-it routes through LiteLLM

- **WHEN** `chat("hello", "s1", False, model="gemini:gemma-4-26b-a4b-it")` is called with `GEMINI_API_KEY` set
- **THEN** `litellm.completion` is invoked with `model="gemini/gemma-4-26b-a4b-it"` and `api_key=<GEMINI_API_KEY value>`, and `google.genai.Client` is NOT constructed

#### Scenario: Bare gemini-2.5-flash still uses native SDK

- **WHEN** `chat("hello", "s1", False, model="gemini-2.5-flash")` is called
- **THEN** `google.genai.Client(...)` is constructed and `client.models.generate_content(...)` is invoked; `litellm.completion` is NOT called

#### Scenario: Missing GEMINI_API_KEY raises for gemini: prefix

- **WHEN** `chat(..., model="gemini:gemma-4-26b-a4b-it")` is called with `GEMINI_API_KEY` unset
- **THEN** `ToolCallError` is raised with a message containing `GEMINI_API_KEY`

<!-- @trace
source: interactive-model-picker
updated: 2026-04-24
code:
  - src/ghibli/sessions.py
  - README.md
  - .env.example
  - CLAUDE.md
  - src/ghibli/cli.py
  - src/ghibli/picker.py
  - src/ghibli/agent.py
  - evals/models.py
tests:
  - tests/unit/test_agent.py
  - tests/unit/test_cli.py
  - tests/unit/test_picker.py
  - tests/unit/test_sessions.py
-->