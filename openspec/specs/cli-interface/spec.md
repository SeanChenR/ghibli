# cli-interface Specification

## Purpose

TBD - created by archiving change 'cli-entry-point'. Update Purpose after archive.

## Requirements

### Requirement: Conversation loop starts on launch

The CLI SHALL enter an interactive multi-turn conversation loop when the user runs `ghibli` with no positional arguments. Each iteration SHALL read one line of user input, dispatch it to the agent layer, and print the response. The loop SHALL continue until the user sends an empty line, `Ctrl+C`, or `Ctrl+D`.

#### Scenario: Conversation loop reads multiple turns

- **WHEN** the user runs `ghibli` and enters multiple queries sequentially
- **THEN** each query receives a response before the next prompt is shown

#### Scenario: Empty line ends the session

- **WHEN** the user enters an empty line (presses Enter with no text)
- **THEN** the application prints a farewell message and exits with code 0

#### Scenario: Ctrl+C or Ctrl+D ends the session gracefully

- **WHEN** the user sends `KeyboardInterrupt` or `EOFError`
- **THEN** the application prints a farewell message and exits with code 0


<!-- @trace
source: cli-entry-point
updated: 2026-04-22
code:
  - tests/unit/__init__.py
  - .spectra.yaml
  - specs/tech-stack.md
  - src/ghibli/exceptions.py
  - uv.lock
  - CLAUDE.md
  - src/ghibli/tools.py
  - src/ghibli/github_api.py
  - skills-lock.json
  - tests/conftest.py
  - src/ghibli/__init__.py
  - specs/mission.md
  - tests/integration/__init__.py
  - .coverage
  - .env.example
  - src/ghibli/output.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/cli.py
  - src/ghibli/sessions.py
  - pyproject.toml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_github_api.py
  - tests/unit/test_sessions.py
  - tests/unit/test_cli.py
  - tests/integration/test_github_api_integration.py
-->

---
### Requirement: --session flag loads an existing session

The CLI SHALL accept `--session <id>` as an option. When provided, the application SHALL pass the session ID to the agent layer so that conversation history is loaded from the SQLite session database before the first turn.

#### Scenario: --session resumes an existing session

- **WHEN** the user runs `ghibli --session abc123`
- **THEN** the agent layer receives `session_id="abc123"` and prior turns are available in context

#### Scenario: Unknown session ID is rejected

- **WHEN** the user passes a session ID that does not exist in the database
- **THEN** the application prints an error to stderr and exits with code 1


<!-- @trace
source: cli-entry-point
updated: 2026-04-22
code:
  - tests/unit/__init__.py
  - .spectra.yaml
  - specs/tech-stack.md
  - src/ghibli/exceptions.py
  - uv.lock
  - CLAUDE.md
  - src/ghibli/tools.py
  - src/ghibli/github_api.py
  - skills-lock.json
  - tests/conftest.py
  - src/ghibli/__init__.py
  - specs/mission.md
  - tests/integration/__init__.py
  - .coverage
  - .env.example
  - src/ghibli/output.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/cli.py
  - src/ghibli/sessions.py
  - pyproject.toml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_github_api.py
  - tests/unit/test_sessions.py
  - tests/unit/test_cli.py
  - tests/integration/test_github_api_integration.py
-->

---
### Requirement: --list-sessions flag lists past sessions

The CLI SHALL accept a `--list-sessions` boolean flag. When present, the application SHALL print a summary of all sessions (id, created_at, title) and exit with code 0.

#### Scenario: --list-sessions prints session table

- **WHEN** the user runs `ghibli --list-sessions`
- **THEN** the application prints each session's id, creation time, and title, then exits with code 0

#### Scenario: --list-sessions with no sessions shows empty state

- **WHEN** there are no saved sessions
- **THEN** the application prints a message indicating no sessions exist and exits with code 0


<!-- @trace
source: cli-entry-point
updated: 2026-04-22
code:
  - tests/unit/__init__.py
  - .spectra.yaml
  - specs/tech-stack.md
  - src/ghibli/exceptions.py
  - uv.lock
  - CLAUDE.md
  - src/ghibli/tools.py
  - src/ghibli/github_api.py
  - skills-lock.json
  - tests/conftest.py
  - src/ghibli/__init__.py
  - specs/mission.md
  - tests/integration/__init__.py
  - .coverage
  - .env.example
  - src/ghibli/output.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/cli.py
  - src/ghibli/sessions.py
  - pyproject.toml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_github_api.py
  - tests/unit/test_sessions.py
  - tests/unit/test_cli.py
  - tests/integration/test_github_api_integration.py
-->

---
### Requirement: --json flag controls output format

The CLI SHALL accept a `--json` boolean flag (default: False). When `True`, all agent responses SHALL be printed as raw JSON. When `False`, the output layer SHALL render Rich-formatted text.

#### Scenario: Default output is Rich format

- **WHEN** the user runs `ghibli` without `--json`
- **THEN** `json_output=False` is passed to the agent layer on every turn

#### Scenario: --json flag enables raw JSON output

- **WHEN** the user runs `ghibli --json`
- **THEN** `json_output=True` is passed to the agent layer on every turn


<!-- @trace
source: cli-entry-point
updated: 2026-04-22
code:
  - tests/unit/__init__.py
  - .spectra.yaml
  - specs/tech-stack.md
  - src/ghibli/exceptions.py
  - uv.lock
  - CLAUDE.md
  - src/ghibli/tools.py
  - src/ghibli/github_api.py
  - skills-lock.json
  - tests/conftest.py
  - src/ghibli/__init__.py
  - specs/mission.md
  - tests/integration/__init__.py
  - .coverage
  - .env.example
  - src/ghibli/output.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/cli.py
  - src/ghibli/sessions.py
  - pyproject.toml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_github_api.py
  - tests/unit/test_sessions.py
  - tests/unit/test_cli.py
  - tests/integration/test_github_api_integration.py
-->

---
### Requirement: --version flag prints version and exits

The CLI SHALL accept a `--version` flag. When present, the application SHALL print `"ghibli <version>"` where `<version>` matches `__version__` from `src/ghibli/__init__.py`, then exit with code 0.

#### Scenario: --version prints version string

- **WHEN** the user runs `ghibli --version`
- **THEN** the application prints the version string (e.g., `"ghibli 0.1.0"`) and exits with code 0

<!-- @trace
source: cli-entry-point
updated: 2026-04-22
code:
  - tests/unit/__init__.py
  - .spectra.yaml
  - specs/tech-stack.md
  - src/ghibli/exceptions.py
  - uv.lock
  - CLAUDE.md
  - src/ghibli/tools.py
  - src/ghibli/github_api.py
  - skills-lock.json
  - tests/conftest.py
  - src/ghibli/__init__.py
  - specs/mission.md
  - tests/integration/__init__.py
  - .coverage
  - .env.example
  - src/ghibli/output.py
  - tests/__init__.py
  - specs/roadmap.md
  - src/ghibli/cli.py
  - src/ghibli/sessions.py
  - pyproject.toml
tests:
  - tests/unit/test_exceptions.py
  - tests/unit/test_github_api.py
  - tests/unit/test_sessions.py
  - tests/unit/test_cli.py
  - tests/integration/test_github_api_integration.py
-->

---
### Requirement: --model flag selects model and bypasses picker

The CLI SHALL accept a `--model <name>` option. When provided, its value SHALL be passed to `agent.chat(...)` as the `model` keyword argument and SHALL take precedence over the `GHIBLI_MODEL` environment variable and `<cwd>/.ghibli/last_model`. Accepted formats include a bare model name (e.g., `gemini-2.5-flash`) and prefixed forms (`openai:<slug>`, `ollama:<slug>`, `gemini:<slug>`).

Passing `--model` SHALL NOT update `<cwd>/.ghibli/last_model` — the value is used for this run only.

#### Scenario: --model takes precedence over GHIBLI_MODEL and last_model

- **WHEN** `GHIBLI_MODEL=gemini-2.5-flash` is set, `<cwd>/.ghibli/last_model` contains `ollama:qwen3.5:cloud`, and the user passes `--model openai:gpt-4o-mini`
- **THEN** `agent.chat` receives `model="openai:gpt-4o-mini"` and `<cwd>/.ghibli/last_model` is unchanged


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
### Requirement: Tool call visualization during agent work

The CLI SHALL pass an `on_tool_call` callback to `agent.chat(...)` that prints each tool dispatch in real time. Each printed line SHALL include the tool name and at minimum one representative argument value (e.g., `→ search_repositories(q="python")`). The line SHALL NOT interleave with the thinking spinner: the spinner SHALL be paused before the line is printed and resumed afterwards (or stopped entirely if no further tool dispatches are expected).

#### Scenario: Dispatching two tools prints two lines

- **WHEN** the user submits a query that causes the agent to call `search_repositories` followed by `get_repository`
- **THEN** the terminal displays two lines during the turn: `→ search_repositories(...)` then `→ get_repository(...)`


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
### Requirement: Welcome banner on start

After picker resolution and before the first `You ❯` prompt, the CLI SHALL print a welcome banner exactly once per invocation. The banner SHALL include the resolved model identifier, the current session ID, and a one-line usage hint.

#### Scenario: New session displays the welcome banner

- **WHEN** the user starts `ghibli` with a resolved model and a fresh session
- **THEN** a banner containing the model name, the session ID, and a short usage hint is printed before the first prompt


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
### Requirement: Thinking spinner during agent work

While `agent.chat()` is executing a single turn, the CLI SHALL display a Rich spinner labeled `Thinking...` to indicate progress. The spinner SHALL NOT be active while `typer.prompt` is reading input and SHALL be paused immediately before any tool visualization line is printed.

#### Scenario: Spinner visible during model latency

- **WHEN** the selected model takes multiple seconds to respond to a turn
- **THEN** a spinner glyph with label `Thinking...` is displayed and updates continuously until the response arrives


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
### Requirement: Session save hint on exit

When the conversation loop ends and the session has one or more persisted turns, the CLI SHALL print the session ID and a resume instruction of the form `Resume with: ghibli --session <id>`. When the session has zero turns, the CLI SHALL NOT print a resume hint (the empty session is deleted per the `session-storage` spec).

#### Scenario: Session with turns prints resume hint

- **WHEN** the user exits after at least one completed user/assistant exchange on a new session
- **THEN** the CLI prints `Session saved: <id> (N turns)` on one line and `Resume with: ghibli --session <id>` on the next line before exiting with code 0

#### Scenario: Empty session prints no resume hint

- **WHEN** the user exits immediately after starting `ghibli` without sending any message
- **THEN** the CLI prints only a brief farewell and exits; no `Resume with:` line is printed and `--list-sessions` does not include this session afterwards


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
### Requirement: --help excludes Typer completion commands

The CLI SHALL initialize the Typer application with `add_completion=False` so that the auto-generated options `--install-completion` and `--show-completion` do not appear in `ghibli --help` output.

#### Scenario: --help output hides completion options

- **WHEN** the user runs `ghibli --help`
- **THEN** the printed options list contains neither `--install-completion` nor `--show-completion`

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