# gemini-authentication Specification

## Purpose

TBD - created by archiving change 'github-tools'. Update Purpose after archive.

## Requirements

### Requirement: Gemini client initialized with API Key when GEMINI_API_KEY is set

When the environment variable `GEMINI_API_KEY` is present, `agent.py` SHALL initialize the Gemini client as `google.genai.Client(api_key=os.environ["GEMINI_API_KEY"])`. API Key mode takes priority over Vertex AI mode.

#### Scenario: GEMINI_API_KEY present uses API Key client

- **WHEN** `GEMINI_API_KEY` is set in the environment
- **THEN** `google.genai.Client` is initialized with `api_key=<value>` and no Vertex AI parameters


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
### Requirement: Gemini client initialized with Vertex AI when GEMINI_API_KEY is absent

When `GEMINI_API_KEY` is not set but `VERTEX_PROJECT` is present, `agent.py` SHALL initialize the Gemini client as `google.genai.Client(vertexai=True, project=os.environ["VERTEX_PROJECT"], location=os.environ.get("VERTEX_LOCATION", "us-central1"))`. Google ADC (Application Default Credentials) must be configured in the environment for this to work.

#### Scenario: VERTEX_PROJECT present uses Vertex AI client

- **WHEN** `GEMINI_API_KEY` is absent and `VERTEX_PROJECT` is set
- **THEN** `google.genai.Client` is initialized with `vertexai=True`, `project=<VERTEX_PROJECT>`, and `location=<VERTEX_LOCATION or "us-central1">`


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
### Requirement: Missing authentication raises ToolCallError at chat() call time

When neither `GEMINI_API_KEY` nor `VERTEX_PROJECT` is set, the `chat()` function SHALL raise `ToolCallError` with a message indicating that Gemini authentication is not configured.

#### Scenario: No credentials raises ToolCallError

- **WHEN** both `GEMINI_API_KEY` and `VERTEX_PROJECT` are absent from the environment
- **THEN** `chat()` raises `ToolCallError` with a message containing `"GEMINI_API_KEY"` and `"VERTEX_PROJECT"`

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