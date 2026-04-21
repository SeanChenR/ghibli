## ADDED Requirements

### Requirement: Package metadata and dependencies declared in pyproject.toml

The project SHALL declare all runtime and development dependencies in `pyproject.toml` using PEP 621 metadata. Runtime dependencies SHALL include `typer`, `google-genai`, `rich`, `httpx`, and `python-dotenv`. Development dependencies SHALL include `pytest`, `pytest-cov`, `ruff`, and `black`.

#### Scenario: Runtime dependencies are installable

- **WHEN** a developer runs `uv sync` in a clean environment
- **THEN** all runtime dependencies are installed without error and `import ghibli` succeeds

#### Scenario: Dev dependencies are installable

- **WHEN** a developer runs `uv sync --dev` in a clean environment
- **THEN** all development tools (`pytest`, `ruff`, `black`) are available on the PATH

### Requirement: CLI entry point registered as a script

The project SHALL register `ghibli` as a console script entry point in `pyproject.toml`, pointing to `ghibli.cli:app`.

#### Scenario: CLI is invokable after install

- **WHEN** the package is installed via `uv pip install -e .`
- **THEN** running `ghibli --help` displays the top-level help message without error

### Requirement: Source layout follows src/ convention

The package source code SHALL reside under `src/ghibli/`. The `pyproject.toml` SHALL configure `[tool.setuptools.packages.find]` (or equivalent for uv) to find packages under `src/`.

#### Scenario: Package is importable from src layout

- **WHEN** the project is installed in editable mode
- **THEN** `from ghibli.cli import app` resolves without `ModuleNotFoundError`

### Requirement: Test tooling configured in pyproject.toml

The project SHALL configure pytest, ruff, and black settings in `pyproject.toml`. pytest SHALL be configured with `testpaths = ["tests"]` and `addopts = "--cov=ghibli --cov-report=term-missing"`. Minimum coverage threshold SHALL be 80% for branches, functions, lines, and statements.

#### Scenario: pytest discovers and runs tests

- **WHEN** a developer runs `pytest` from the project root
- **THEN** pytest finds test files under `tests/` and reports results

#### Scenario: Coverage threshold enforced

- **WHEN** overall line coverage falls below 80%
- **THEN** `pytest --cov` exits with a non-zero exit code

### Requirement: Environment variable template provided

The project SHALL include a `.env.example` file listing all required and optional environment variables with descriptions. The file SHALL document that exactly one of two Gemini authentication methods is required: either `GEMINI_API_KEY` (API key mode) or `VERTEX_PROJECT` (Vertex AI mode). Optional variables SHALL be `VERTEX_LOCATION` (defaults to `us-central1` when using Vertex AI) and `GITHUB_TOKEN`.

#### Scenario: Developer knows required env vars

- **WHEN** a developer clones the repository
- **THEN** `.env.example` lists every environment variable the application reads, with a comment explaining each one

### Requirement: Test directory structure established

The project SHALL have a `tests/` directory with `unit/` and `integration/` subdirectories, each containing an `__init__.py`. A root `tests/conftest.py` SHALL exist for shared pytest fixtures.

#### Scenario: Unit and integration tests are independently runnable

- **WHEN** a developer runs `pytest tests/unit/`
- **THEN** only unit tests execute, with no import errors from missing `__init__.py`
