# exception-hierarchy Specification

## Purpose

TBD - created by archiving change 'project-scaffold'. Update Purpose after archive.

## Requirements

### Requirement: Base exception class GhibliError defined

The module `src/ghibli/exceptions.py` SHALL define a `GhibliError` base exception class that inherits from `Exception`. All application-specific exceptions SHALL inherit from `GhibliError`.

#### Scenario: GhibliError is catchable as Exception

- **WHEN** code raises any `GhibliError` subclass
- **THEN** a bare `except Exception` block catches it

#### Scenario: GhibliError is catchable as GhibliError

- **WHEN** code raises any `GhibliError` subclass
- **THEN** `except GhibliError` catches it without naming the specific subclass


<!-- @trace
source: project-scaffold
updated: 2026-04-22
code:
  - specs/tech-stack.md
  - tests/integration/__init__.py
  - tests/unit/__init__.py
  - .spectra.yaml
  - .env.example
  - src/ghibli/github_api.py
  - src/ghibli/output.py
  - uv.lock
  - src/ghibli/tools.py
  - tests/__init__.py
  - src/ghibli/cli.py
  - src/ghibli/sessions.py
  - CLAUDE.md
  - specs/roadmap.md
  - pyproject.toml
  - specs/mission.md
  - src/ghibli/exceptions.py
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
tests:
  - tests/unit/test_exceptions.py
-->

---
### Requirement: ToolCallError raised for LLM tool-calling failures

The module SHALL define `ToolCallError(GhibliError)` to represent failures when the LLM cannot determine which GitHub tool to call, or when tool call arguments are invalid or the Gemini API is unreachable.

#### Scenario: ToolCallError carries a message

- **WHEN** `ToolCallError` is raised with a message string
- **THEN** `str(error)` returns that message

#### Scenario: ToolCallError is a GhibliError

- **WHEN** code raises `ToolCallError`
- **THEN** `isinstance(error, GhibliError)` is `True`


<!-- @trace
source: project-scaffold
updated: 2026-04-22
code:
  - specs/tech-stack.md
  - tests/integration/__init__.py
  - tests/unit/__init__.py
  - .spectra.yaml
  - .env.example
  - src/ghibli/github_api.py
  - src/ghibli/output.py
  - uv.lock
  - src/ghibli/tools.py
  - tests/__init__.py
  - src/ghibli/cli.py
  - src/ghibli/sessions.py
  - CLAUDE.md
  - specs/roadmap.md
  - pyproject.toml
  - specs/mission.md
  - src/ghibli/exceptions.py
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
tests:
  - tests/unit/test_exceptions.py
-->

---
### Requirement: GitHubAPIError raised for GitHub REST API failures

The module SHALL define `GitHubAPIError(GhibliError)` to represent HTTP-level failures when calling the GitHub REST API. It SHALL store the HTTP status code as an integer attribute `status_code`.

#### Scenario: GitHubAPIError exposes status_code

- **WHEN** `GitHubAPIError` is raised with `status_code=404`
- **THEN** `error.status_code` equals `404`

#### Scenario: GitHubAPIError is a GhibliError

- **WHEN** code raises `GitHubAPIError`
- **THEN** `isinstance(error, GhibliError)` is `True`


<!-- @trace
source: project-scaffold
updated: 2026-04-22
code:
  - specs/tech-stack.md
  - tests/integration/__init__.py
  - tests/unit/__init__.py
  - .spectra.yaml
  - .env.example
  - src/ghibli/github_api.py
  - src/ghibli/output.py
  - uv.lock
  - src/ghibli/tools.py
  - tests/__init__.py
  - src/ghibli/cli.py
  - src/ghibli/sessions.py
  - CLAUDE.md
  - specs/roadmap.md
  - pyproject.toml
  - specs/mission.md
  - src/ghibli/exceptions.py
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
tests:
  - tests/unit/test_exceptions.py
-->

---
### Requirement: SessionError raised for session storage failures

The module SHALL define `SessionError(GhibliError)` to represent failures when reading from or writing to the SQLite session database at `~/.ghibli/sessions.db`.

#### Scenario: SessionError is a GhibliError

- **WHEN** code raises `SessionError`
- **THEN** `isinstance(error, GhibliError)` is `True`


<!-- @trace
source: project-scaffold
updated: 2026-04-22
code:
  - specs/tech-stack.md
  - tests/integration/__init__.py
  - tests/unit/__init__.py
  - .spectra.yaml
  - .env.example
  - src/ghibli/github_api.py
  - src/ghibli/output.py
  - uv.lock
  - src/ghibli/tools.py
  - tests/__init__.py
  - src/ghibli/cli.py
  - src/ghibli/sessions.py
  - CLAUDE.md
  - specs/roadmap.md
  - pyproject.toml
  - specs/mission.md
  - src/ghibli/exceptions.py
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
tests:
  - tests/unit/test_exceptions.py
-->

---
### Requirement: OutputError raised for output formatting failures

The module SHALL define `OutputError(GhibliError)` to represent failures when formatting or rendering the response.

#### Scenario: OutputError is a GhibliError

- **WHEN** code raises `OutputError`
- **THEN** `isinstance(error, GhibliError)` is `True`

<!-- @trace
source: project-scaffold
updated: 2026-04-22
code:
  - specs/tech-stack.md
  - tests/integration/__init__.py
  - tests/unit/__init__.py
  - .spectra.yaml
  - .env.example
  - src/ghibli/github_api.py
  - src/ghibli/output.py
  - uv.lock
  - src/ghibli/tools.py
  - tests/__init__.py
  - src/ghibli/cli.py
  - src/ghibli/sessions.py
  - CLAUDE.md
  - specs/roadmap.md
  - pyproject.toml
  - specs/mission.md
  - src/ghibli/exceptions.py
  - skills-lock.json
  - src/ghibli/__init__.py
  - tests/conftest.py
tests:
  - tests/unit/test_exceptions.py
-->