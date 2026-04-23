## MODIFIED Requirements

### Requirement: Interactive model picker on launch

The CLI SHALL present an interactive model picker BEFORE entering the conversation loop when either of the following is true:

(a) the `--model-picker` flag was passed; OR
(b) ALL of the following are true:
    - no `--model` flag was passed,
    - `GHIBLI_MODEL` is not set in the environment, and
    - `<cwd>/.ghibli/last_model` does not exist or is empty.

The picker SHALL always present 5 options regardless of environment state:

1. Gemini 2.5 Flash (API Key)
2. Gemini 2.5 Flash (Vertex AI)
3. Gemma-4-26b (open-weight, via Gemini API)
4. OpenAI gpt-4o-mini
5. Ollama Cloud (model id taken from `OLLAMA_CLOUD_MODEL` env var; default `qwen3.5:cloud`)

The picker SHALL read the user's choice via `typer.prompt("Select", default=1, type=int)` and SHALL NOT filter the list by whether required environment variables are already set.

After the user makes a choice, the CLI SHALL write the chosen model identifier to `<cwd>/.ghibli/last_model` so the next run can resume directly.

#### Scenario: Picker with 5 options appears on first launch

- **WHEN** the user runs `ghibli` with no `--model`, no `GHIBLI_MODEL` set, and no `<cwd>/.ghibli/last_model` file
- **THEN** the CLI prints all 5 provider options as a numbered list regardless of which API keys are present in the environment

#### Scenario: Picker is skipped when last_model exists

- **WHEN** `<cwd>/.ghibli/last_model` contains `openai:gpt-4o-mini`, no `--model` flag is passed, and `GHIBLI_MODEL` is not set
- **THEN** the CLI uses `openai:gpt-4o-mini` directly, enters the conversation loop without prompting, and does NOT print a picker menu

#### Scenario: --model flag takes precedence over last_model

- **WHEN** `<cwd>/.ghibli/last_model` contains `openai:gpt-4o-mini` and the user passes `--model gemini:gemma-4-26b-a4b-it`
- **THEN** the CLI uses `gemini:gemma-4-26b-a4b-it` and does NOT prompt a picker

#### Scenario: Selection is persisted to last_model

- **WHEN** the picker is shown and the user selects option 4 (OpenAI gpt-4o-mini)
- **THEN** `<cwd>/.ghibli/last_model` is written with exactly the line `openai:gpt-4o-mini\n` before entering the conversation loop

### Requirement: Zero-provider onboarding writes key to .env

When the user selects a model in the picker but the corresponding provider is missing required credentials, the CLI SHALL run an onboarding sub-flow scoped to that provider:

- For **API Key providers** (Gemini 2.5 Flash API Key / Gemma-4 / OpenAI / Ollama Cloud): prompt the user to paste the relevant API key via `typer.prompt(hide_input=True)` and append the KEY=value line to `<cwd>/.env` using `append_env_var` from the `gemini-authentication` spec. If the key already exists in `.env`, abort per that spec.
- For **Vertex AI**: the CLI SHALL print a multi-step instruction that includes the literal text `gcloud auth application-default login` for the user to run in another terminal, then prompt for a `GOOGLE_CLOUD_PROJECT` value and append it to `<cwd>/.env`. The CLI SHALL additionally offer to record an optional `GOOGLE_CLOUD_LOCATION` (default `us-central1` when skipped).

After onboarding completes, the CLI SHALL continue into the conversation loop using the newly configured provider AND write the selected model identifier to `<cwd>/.ghibli/last_model`.

#### Scenario: Picker selects API Key provider without key → API Key onboarding

- **WHEN** the user selects OpenAI gpt-4o-mini from the picker and `OPENAI_API_KEY` is not set in the environment or `.env`
- **THEN** the CLI prompts `Paste your OPENAI_API_KEY` with hidden input, then appends `OPENAI_API_KEY=<entered>` to `<cwd>/.env` and proceeds

#### Scenario: Picker selects Vertex AI → ADC onboarding with project prompt

- **WHEN** the user selects Gemini 2.5 Flash (Vertex AI) from the picker and `GOOGLE_CLOUD_PROJECT` is not set
- **THEN** the CLI prints an instruction containing the literal string `gcloud auth application-default login`, prompts for the project id, appends `GOOGLE_CLOUD_PROJECT=<entered>` to `<cwd>/.env`, and proceeds

## ADDED Requirements

### Requirement: --model-picker flag forces re-selection and updates last_model

The CLI SHALL accept a `--model-picker` boolean flag. When this flag is passed, the CLI SHALL:

1. Ignore `--model`, `GHIBLI_MODEL`, and `<cwd>/.ghibli/last_model` as model sources
2. Unconditionally display the picker (even when a `last_model` exists)
3. Write the newly selected model identifier to `<cwd>/.ghibli/last_model`, overwriting any previous value

#### Scenario: --model-picker overrides persisted last_model

- **WHEN** `<cwd>/.ghibli/last_model` contains `openai:gpt-4o-mini` and the user runs `ghibli --model-picker`
- **THEN** the picker is displayed, and after the user selects a different model (e.g., option 2 Gemini Vertex AI), `<cwd>/.ghibli/last_model` is overwritten with the new identifier

### Requirement: Model resolution priority (no silent default)

Before entering the conversation loop, the CLI SHALL resolve the model identifier by checking the following sources in order and SHALL use the first one found:

1. `--model <id>` command-line flag
2. `GHIBLI_MODEL` environment variable
3. `<cwd>/.ghibli/last_model` file contents (stripped)
4. Picker selection (writes the chosen value back to `<cwd>/.ghibli/last_model`)

When `--model-picker` is passed, sources 1–3 SHALL be ignored and source 4 is always used.

The CLI SHALL NOT fall back to any hard-coded model name such as `gemini-2.5-flash`. If source 4 is unreachable (e.g., stdin is not a TTY), the CLI SHALL exit with code 1 and print an error message instructing the user to pass `--model` or set `GHIBLI_MODEL`.

#### Scenario: All sources empty on non-TTY stdin → exits with error

- **WHEN** the user pipes input (stdin is not a TTY), no `--model` flag, no `GHIBLI_MODEL`, no `<cwd>/.ghibli/last_model`
- **THEN** the CLI prints an error to stderr containing `--model` and exits with code 1

#### Scenario: GHIBLI_MODEL wins over last_model

- **WHEN** `GHIBLI_MODEL=openai:gpt-4o-mini` and `<cwd>/.ghibli/last_model` contains `ollama:qwen3.5:cloud`
- **THEN** the CLI uses `openai:gpt-4o-mini`

### Requirement: Project-local .env read only

The CLI SHALL load the dotenv file from `<cwd>/.env` using an explicit path (e.g., `load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)`) and SHALL NOT allow `find_dotenv()` to walk up parent directories.

#### Scenario: Home .env is not loaded

- **WHEN** `/Users/<user>/.env` contains `GOOGLE_CLOUD_PROJECT=my-project` but `<cwd>/.env` does not exist or does not contain that variable
- **THEN** `os.environ.get("GOOGLE_CLOUD_PROJECT")` remains unchanged from its pre-CLI value (the CLI does NOT inject the home-directory value)

## ADDED Requirements

### Requirement: --model flag selects model and bypasses picker

The CLI SHALL accept a `--model <name>` option. When provided, its value SHALL be passed to `agent.chat(...)` as the `model` keyword argument and SHALL take precedence over the `GHIBLI_MODEL` environment variable and `<cwd>/.ghibli/last_model`. Accepted formats include a bare model name (e.g., `gemini-2.5-flash`) and prefixed forms (`openai:<slug>`, `ollama:<slug>`, `gemini:<slug>`).

Passing `--model` SHALL NOT update `<cwd>/.ghibli/last_model` — the value is used for this run only.

#### Scenario: --model takes precedence over GHIBLI_MODEL and last_model

- **WHEN** `GHIBLI_MODEL=gemini-2.5-flash` is set, `<cwd>/.ghibli/last_model` contains `ollama:qwen3.5:cloud`, and the user passes `--model openai:gpt-4o-mini`
- **THEN** `agent.chat` receives `model="openai:gpt-4o-mini"` and `<cwd>/.ghibli/last_model` is unchanged

### Requirement: Tool call visualization during agent work

The CLI SHALL pass an `on_tool_call` callback to `agent.chat(...)` that prints each tool dispatch in real time. Each printed line SHALL include the tool name and at minimum one representative argument value (e.g., `→ search_repositories(q="python")`). The line SHALL NOT interleave with the thinking spinner: the spinner SHALL be paused before the line is printed and resumed afterwards (or stopped entirely if no further tool dispatches are expected).

#### Scenario: Dispatching two tools prints two lines

- **WHEN** the user submits a query that causes the agent to call `search_repositories` followed by `get_repository`
- **THEN** the terminal displays two lines during the turn: `→ search_repositories(...)` then `→ get_repository(...)`

### Requirement: Welcome banner on start

After picker resolution and before the first `You ❯` prompt, the CLI SHALL print a welcome banner exactly once per invocation. The banner SHALL include the resolved model identifier, the current session ID, and a one-line usage hint.

#### Scenario: New session displays the welcome banner

- **WHEN** the user starts `ghibli` with a resolved model and a fresh session
- **THEN** a banner containing the model name, the session ID, and a short usage hint is printed before the first prompt

### Requirement: Thinking spinner during agent work

While `agent.chat()` is executing a single turn, the CLI SHALL display a Rich spinner labeled `Thinking...` to indicate progress. The spinner SHALL NOT be active while `typer.prompt` is reading input and SHALL be paused immediately before any tool visualization line is printed.

#### Scenario: Spinner visible during model latency

- **WHEN** the selected model takes multiple seconds to respond to a turn
- **THEN** a spinner glyph with label `Thinking...` is displayed and updates continuously until the response arrives

### Requirement: Session save hint on exit

When the conversation loop ends and the session has one or more persisted turns, the CLI SHALL print the session ID and a resume instruction of the form `Resume with: ghibli --session <id>`. When the session has zero turns, the CLI SHALL NOT print a resume hint (the empty session is deleted per the `session-storage` spec).

#### Scenario: Session with turns prints resume hint

- **WHEN** the user exits after at least one completed user/assistant exchange on a new session
- **THEN** the CLI prints `Session saved: <id> (N turns)` on one line and `Resume with: ghibli --session <id>` on the next line before exiting with code 0

#### Scenario: Empty session prints no resume hint

- **WHEN** the user exits immediately after starting `ghibli` without sending any message
- **THEN** the CLI prints only a brief farewell and exits; no `Resume with:` line is printed and `--list-sessions` does not include this session afterwards

### Requirement: --help excludes Typer completion commands

The CLI SHALL initialize the Typer application with `add_completion=False` so that the auto-generated options `--install-completion` and `--show-completion` do not appear in `ghibli --help` output.

#### Scenario: --help output hides completion options

- **WHEN** the user runs `ghibli --help`
- **THEN** the printed options list contains neither `--install-completion` nor `--show-completion`
