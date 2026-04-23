## ADDED Requirements

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
