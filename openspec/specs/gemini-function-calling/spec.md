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