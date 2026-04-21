## ADDED Requirements

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

### Requirement: --session flag loads an existing session

The CLI SHALL accept `--session <id>` as an option. When provided, the application SHALL pass the session ID to the agent layer so that conversation history is loaded from the SQLite session database before the first turn.

#### Scenario: --session resumes an existing session

- **WHEN** the user runs `ghibli --session abc123`
- **THEN** the agent layer receives `session_id="abc123"` and prior turns are available in context

#### Scenario: Unknown session ID is rejected

- **WHEN** the user passes a session ID that does not exist in the database
- **THEN** the application prints an error to stderr and exits with code 1

### Requirement: --list-sessions flag lists past sessions

The CLI SHALL accept a `--list-sessions` boolean flag. When present, the application SHALL print a summary of all sessions (id, created_at, title) and exit with code 0.

#### Scenario: --list-sessions prints session table

- **WHEN** the user runs `ghibli --list-sessions`
- **THEN** the application prints each session's id, creation time, and title, then exits with code 0

#### Scenario: --list-sessions with no sessions shows empty state

- **WHEN** there are no saved sessions
- **THEN** the application prints a message indicating no sessions exist and exits with code 0

### Requirement: --json flag controls output format

The CLI SHALL accept a `--json` boolean flag (default: False). When `True`, all agent responses SHALL be printed as raw JSON. When `False`, the output layer SHALL render Rich-formatted text.

#### Scenario: Default output is Rich format

- **WHEN** the user runs `ghibli` without `--json`
- **THEN** `json_output=False` is passed to the agent layer on every turn

#### Scenario: --json flag enables raw JSON output

- **WHEN** the user runs `ghibli --json`
- **THEN** `json_output=True` is passed to the agent layer on every turn

### Requirement: --version flag prints version and exits

The CLI SHALL accept a `--version` flag. When present, the application SHALL print `"ghibli <version>"` where `<version>` matches `__version__` from `src/ghibli/__init__.py`, then exit with code 0.

#### Scenario: --version prints version string

- **WHEN** the user runs `ghibli --version`
- **THEN** the application prints the version string (e.g., `"ghibli 0.1.0"`) and exits with code 0
