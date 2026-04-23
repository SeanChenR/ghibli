## ADDED Requirements

### Requirement: append_env_var persists a new API key to .env without overwriting

The module `src/ghibli/picker.py` SHALL expose `append_env_var(key: str, value: str, env_path: Path | None = None) -> None` that writes an environment variable assignment to a dotenv-format file. When `env_path` is `None`, the implementation SHALL default to `.env` in the current working directory. The function SHALL use UTF-8 encoding and explicit `"\n"` line terminators. Behavior is defined by the following cases:

1. When `env_path` does not exist, the function SHALL create it containing exactly one line `<key>=<value>\n`.
2. When `env_path` exists and does NOT contain any line matching the regular expression `^<key>=` (anchored at line start), the function SHALL append `<key>=<value>\n`, first inserting a newline if the file does not end with one.
3. When `env_path` exists AND contains a line matching `^<key>=` (regardless of the line's current value), the function SHALL NOT modify the file and SHALL raise `SessionError` with a message identifying the key and instructing the user to edit `.env` manually.

The function SHALL NOT execute any network request and SHALL NOT validate the value.

#### Scenario: Creates new .env when absent

- **WHEN** `.env` does not exist in the current directory and `append_env_var("GEMINI_API_KEY", "AI123")` is called
- **THEN** a file `.env` is created whose entire content equals `GEMINI_API_KEY=AI123\n`

#### Scenario: Appends to existing .env without duplicate key

- **WHEN** `.env` contains exactly the line `OPENAI_API_KEY=sk-existing\n` and `append_env_var("GEMINI_API_KEY", "AI123")` is called
- **THEN** `.env` contains two lines in order: `OPENAI_API_KEY=sk-existing\n` followed by `GEMINI_API_KEY=AI123\n`

#### Scenario: Refuses to overwrite existing key

- **WHEN** `.env` contains `GEMINI_API_KEY=AI-old\n` and `append_env_var("GEMINI_API_KEY", "AI-new")` is called
- **THEN** `.env` is not modified (its bytes are unchanged) and the function raises an exception whose message contains `GEMINI_API_KEY`

### Requirement: Onboarding flow uses append_env_var for API Key providers

During onboarding (defined in the `cli-interface` spec), when the user selects an **API Key** provider (Gemini 2.5 Flash API Key / Gemma-4 / OpenAI gpt-4o-mini / Ollama Cloud), the CLI SHALL call `append_env_var(<chosen_env_var>, <user_input>)` to persist the API key before continuing into the conversation loop. If `append_env_var` raises due to an existing key, the CLI SHALL print the exception message and exit with code 0 without entering the loop (the user must edit `.env` manually and re-run).

#### Scenario: Setup flow appends new key and enters conversation

- **WHEN** onboarding is active, the user selects OpenAI, and enters the key `sk-new`
- **THEN** `append_env_var("OPENAI_API_KEY", "sk-new")` is called, succeeds, and the CLI enters the conversation loop with OpenAI gpt-4o-mini as the selected model

#### Scenario: Setup flow aborts when the key already exists

- **WHEN** onboarding is active, the user selects OpenAI, enters a key, and `append_env_var` raises because `.env` already has `OPENAI_API_KEY=<something>`
- **THEN** the CLI prints the exception message, does NOT modify `.env`, does NOT enter the conversation loop, and exits with code 0

### Requirement: Vertex AI onboarding guides user through ADC setup

During onboarding, when the user selects **Gemini 2.5 Flash (Vertex AI)**, the CLI SHALL:

1. Print an instruction containing the literal string `gcloud auth application-default login` and wait for the user to press Enter confirming they completed the command in another terminal
2. Prompt for the GCP project id via `typer.prompt("Paste your GOOGLE_CLOUD_PROJECT")`
3. Optionally prompt for Vertex AI location via `typer.prompt("GOOGLE_CLOUD_LOCATION", default="us-central1")` (the default `us-central1` SHALL be used if the user accepts without typing)
4. Call `append_env_var("GOOGLE_CLOUD_PROJECT", <entered>)` and, when the location was explicitly changed from the default, `append_env_var("GOOGLE_CLOUD_LOCATION", <entered>)`
5. Continue into the conversation loop using `gemini-2.5-flash` as the resolved model (which the native Gemini SDK will route through Vertex AI because `GOOGLE_CLOUD_PROJECT` is now set)

The CLI SHALL NOT attempt to invoke `gcloud` itself or validate ADC state.

#### Scenario: Vertex AI onboarding writes project id to .env

- **WHEN** the user selects Gemini 2.5 Flash (Vertex AI), presses Enter after seeing the ADC instruction, enters `my-project` as project id, and accepts the default location
- **THEN** `.env` contains `GOOGLE_CLOUD_PROJECT=my-project\n` (and does NOT contain `GOOGLE_CLOUD_LOCATION` since the user accepted the default) and the CLI enters the conversation loop

#### Scenario: Vertex AI instruction mentions gcloud ADC command

- **WHEN** the user selects Gemini 2.5 Flash (Vertex AI)
- **THEN** the printed instructions include the exact substring `gcloud auth application-default login`

### Requirement: .env loading is restricted to the current working directory

The CLI entry point in `src/ghibli/cli.py` SHALL load environment variables from `<cwd>/.env` using an explicit `dotenv_path` argument (e.g., `load_dotenv(dotenv_path=Path.cwd() / ".env", override=True)`). The CLI SHALL NOT rely on python-dotenv's default `find_dotenv()` behavior, which walks up parent directories and SHALL NOT load `.env` files from any directory other than `<cwd>`.

#### Scenario: Home directory .env is ignored

- **WHEN** the user's home directory contains `.env` with `GOOGLE_CLOUD_PROJECT=my-personal-project` but the current working directory does not have a `.env` file
- **THEN** after the CLI starts, `os.environ.get("GOOGLE_CLOUD_PROJECT")` returns whatever the shell had before (which may be `None`); the home-directory value is NOT injected
