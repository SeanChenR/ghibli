## ADDED Requirements

### Requirement: Eval runner accepts a model selector flag

The script `evals/run_evals.py` SHALL accept a `--model` CLI option that selects which LLM backend to use for the evaluation run. Valid values are `gemini` (default), `gpt4o-mini`, and `llama3`. The selected model name SHALL be recorded in the run object written to `results.json`.

#### Scenario: Default run uses Gemini

- **WHEN** `run_evals.py` is invoked without `--model`
- **THEN** the run executes using `gemini/gemini-2.5-flash` and the run object's `model` field equals `"gemini"`

#### Scenario: GPT-4o-mini run is selected explicitly

- **WHEN** `run_evals.py --model gpt4o-mini` is invoked
- **THEN** the run executes using `openai/gpt-4o-mini` and the run object's `model` field equals `"gpt4o-mini"`

#### Scenario: Llama 3 run uses Groq

- **WHEN** `run_evals.py --model llama3` is invoked
- **THEN** the run executes using `groq/llama-3.3-70b-versatile` and the run object's `model` field equals `"llama3"`

#### Scenario: Unknown model name raises error

- **WHEN** `run_evals.py --model unknown` is invoked
- **THEN** the CLI prints an error message listing valid model names and exits with a non-zero status code

---

### Requirement: models.py exposes a unified chat interface for all supported models

The module `evals/models.py` SHALL provide a function `chat_with_model(user_message: str, session_id: str, model_name: str) -> tuple[str, list[str]]` that returns the model's text response and the list of tool names called, using LiteLLM with OpenAI-compatible function calling.

#### Scenario: Gemini model returns response and tool list

- **WHEN** `chat_with_model("search Python repos", session_id, "gemini")` is called
- **THEN** it returns a non-empty string response and a `tools_called` list that reflects actual function call names

#### Scenario: Rate-limit delay is applied between Groq calls

- **WHEN** the selected model is `llama3`
- **THEN** `chat_with_model` waits at least 1 second before returning, to avoid exceeding Groq's free-tier RPM limit

#### Scenario: Missing API key raises descriptive error

- **WHEN** the required API key for the selected model is absent from the environment
- **THEN** `chat_with_model` raises a `ToolCallError` with a message identifying the missing variable name

---

### Requirement: Tool schemas are exported in OpenAI-compatible format

The module `evals/tool_schema.py` SHALL provide a function `get_openai_tool_schemas() -> list[dict]` that returns all six GitHub tools as OpenAI-compatible tool schema dicts (with `type`, `function.name`, `function.description`, `function.parameters` keys), suitable for passing as the `tools` argument to LiteLLM.

#### Scenario: Schema list contains all six tools

- **WHEN** `get_openai_tool_schemas()` is called
- **THEN** it returns a list of exactly 6 dicts, one for each of: `search_repositories`, `get_repository`, `list_issues`, `list_pull_requests`, `get_user`, `list_releases`

#### Scenario: Each schema has required OpenAI structure

- **WHEN** any schema dict is inspected
- **THEN** it has keys `type` (value `"function"`), `function.name` (string), `function.description` (string), and `function.parameters` (JSON Schema object)
