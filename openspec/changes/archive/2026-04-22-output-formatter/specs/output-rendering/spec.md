## ADDED Requirements

### Requirement: render_text function accepts text and json_output flag

The function `render_text(text: str, json_output: bool) -> None` in `src/ghibli/output.py` SHALL accept a Gemini response text string and a boolean `json_output` flag, and write formatted output to stdout.

#### Scenario: Function accepts non-empty text

- **WHEN** `render_text("Here are the top Python repositories...", json_output=False)` is called
- **THEN** the function completes without error

#### Scenario: Empty text prints placeholder

- **WHEN** `render_text("", json_output=False)` is called
- **THEN** stdout contains `"(no response)"`

### Requirement: Markdown output mode renders Rich Markdown

When `json_output=False`, the function SHALL render `text` as `rich.markdown.Markdown` using `rich.console.Console().print()`. This allows Gemini responses containing Markdown formatting (bold, tables, code blocks) to be rendered as styled terminal output.

#### Scenario: Markdown text is rendered

- **WHEN** `render_text("**Top repos:**\n- react\n- vue", json_output=False)` is called
- **THEN** the function calls `Console().print(Markdown(...))` without error and output is non-empty

#### Scenario: Plain text renders without error

- **WHEN** `render_text("Found 3 repositories matching your query.", json_output=False)` is called
- **THEN** stdout is non-empty

### Requirement: JSON output mode renders response wrapped in JSON

When `json_output=True`, the function SHALL output `{"response": text}` as a JSON string with 2-space indentation and `ensure_ascii=False` (preserving Unicode characters including Chinese).

#### Scenario: JSON output wraps text in response key

- **WHEN** `render_text("找到 3 個倉庫", json_output=True)` is called
- **THEN** stdout contains `"response"` key and `"找到 3 個倉庫"` without Unicode escape sequences
