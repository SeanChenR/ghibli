# eval-harness Specification

## Purpose

TBD - created by archiving change 'eval-framework'. Update Purpose after archive.

## Requirements

### Requirement: Query catalog defines categorized test cases

The file `evals/queries.yaml` SHALL contain at least 30 test queries organized into five categories: `fuzzy`, `typo`, `contradiction`, `multilingual`, and `multi_step`. Each query entry SHALL include: `id` (string, unique), `category` (one of the five), `query` (the natural language string), `expected_behavior` (human-readable description of expected tool call or model behavior), `difficulty` (`easy`, `medium`, or `hard`), and `notes` (explanation of why this case is interesting or hard).

#### Scenario: Catalog has minimum 30 queries

- **WHEN** `evals/queries.yaml` is loaded
- **THEN** it contains at least 30 entries, at least 5 per category

#### Scenario: Each entry has required fields

- **WHEN** any entry in `evals/queries.yaml` is read
- **THEN** it has non-empty values for `id`, `category`, `query`, `expected_behavior`, `difficulty`, and `notes`

#### Scenario: Category values are valid

- **WHEN** any entry's `category` field is read
- **THEN** it is one of: `fuzzy`, `typo`, `contradiction`, `multilingual`, `multi_step`


<!-- @trace
source: eval-framework
updated: 2026-04-22
code:
  - uv.lock
  - src/ghibli/cli.py
  - evals/queries.yaml
  - .env.example
  - pyproject.toml
  - evals/results.json
  - evals/run_evals.py
  - src/ghibli/github_api.py
  - src/ghibli/agent.py
  - README.md
  - evals/__init__.py
tests:
  - tests/unit/test_eval_runner.py
  - tests/unit/test_eval_queries.py
-->

---
### Requirement: Eval runner executes queries against real agent

The script `evals/run_evals.py` SHALL accept an optional `--category` flag to filter by category, execute each query by calling `agent.chat()` with a fresh session, and write results to `evals/results.json`.

#### Scenario: Runner executes all queries without filter

- **WHEN** `python evals/run_evals.py` is run
- **THEN** it processes all entries in `queries.yaml` and writes a run object to `results.json`

#### Scenario: Runner filters by category

- **WHEN** `python evals/run_evals.py --category typo` is run
- **THEN** only queries with `category: typo` are executed

#### Scenario: Runner handles agent exceptions without stopping

- **WHEN** `agent.chat()` raises a `GhibliError` for one query
- **THEN** that entry is recorded with `status: error` and `error_message` populated, and the runner continues to the next query


<!-- @trace
source: eval-framework
updated: 2026-04-22
code:
  - uv.lock
  - src/ghibli/cli.py
  - evals/queries.yaml
  - .env.example
  - pyproject.toml
  - evals/results.json
  - evals/run_evals.py
  - src/ghibli/github_api.py
  - src/ghibli/agent.py
  - README.md
  - evals/__init__.py
tests:
  - tests/unit/test_eval_runner.py
  - tests/unit/test_eval_queries.py
-->

---
### Requirement: Results file captures structured run output

The file `evals/results.json` SHALL contain a JSON array of run objects. Each run object SHALL include: `run_id` (ISO 8601 timestamp), `model` (string, name of the model used), `total` (int), `passed` (int), `failed` (int), `errors` (int), `accuracy` (float, passed/total), and `results` (array of per-query result objects). Each per-query result SHALL include: `query_id`, `category`, `query`, `status` (`pass`, `fail`, or `error`), `tools_called` (list of tool names), `judge_result` (object with `tool_match`, `sequence_match`, `pass_` booleans), `response_preview` (first 200 chars of response, or empty string), `response_full` (complete model response text), `error_message` (string or null), and `duration_seconds` (float).

#### Scenario: Results file is appended on each run

- **WHEN** `run_evals.py` is run twice
- **THEN** `results.json` contains two run objects in the top-level array

#### Scenario: Run object includes model and accuracy

- **WHEN** a run completes with model `"gpt4o-mini"` and 26 of 30 queries pass
- **THEN** the run object has `model: "gpt4o-mini"` and `accuracy: 0.8666...`

#### Scenario: Per-query result includes judge_result

- **WHEN** a per-query result entry is read
- **THEN** it contains a `judge_result` object with at minimum `tool_match` and `pass_` boolean fields


<!-- @trace
source: multi-model-eval
updated: 2026-04-22
code:
  - evals/compare_models.py
  - README.md
  - evals/results.json
  - specs/eval-hardening-log.md
  - evals/models.py
  - src/ghibli/tool_schema.py
  - src/ghibli/tools.py
  - evals/run_evals.py
  - evals/judge.py
  - .env.example
  - evals/queries.yaml
  - src/ghibli/github_api.py
  - pyproject.toml
  - evals/tool_schema.py
  - CLAUDE.md
  - specs/github-api-capabilities.md
  - src/ghibli/agent.py
  - uv.lock
tests:
  - tests/unit/test_tools.py
  - tests/unit/test_judge.py
  - tests/unit/test_eval_runner.py
  - tests/unit/test_models.py
  - tests/unit/test_compare_models.py
  - tests/unit/test_agent.py
  - tests/unit/test_eval_queries.py
  - tests/unit/test_tool_schema.py
-->

---
### Requirement: Runner instruments agent to capture tool calls

The runner SHALL instrument `agent.chat()` by patching `ghibli.tools` so that each tool call is intercepted and its name is recorded, without altering the tool's actual return value.

#### Scenario: Tool call names are captured via instrumentation

- **WHEN** `run_evals.py` executes a query that triggers `search_repositories`
- **THEN** the result entry's `tools_called` list contains `"search_repositories"` even though the real GitHub API was called


<!-- @trace
source: eval-framework
updated: 2026-04-22
code:
  - uv.lock
  - src/ghibli/cli.py
  - evals/queries.yaml
  - .env.example
  - pyproject.toml
  - evals/results.json
  - evals/run_evals.py
  - src/ghibli/github_api.py
  - src/ghibli/agent.py
  - README.md
  - evals/__init__.py
tests:
  - tests/unit/test_eval_runner.py
  - tests/unit/test_eval_queries.py
-->

---
### Requirement: README documents known limitations

The `README.md` SHALL contain a "Known Limitations" section that explains why the following three failure categories are fundamentally difficult to resolve: fuzzy inputs (no deterministic mapping to API parameters), contradictory conditions (GitHub API returns empty results rather than rejecting impossible queries), and non-Chinese multilingual inputs (untested behavior, no guarantee of correct tool selection).

#### Scenario: Known limitations section exists in README

- **WHEN** `README.md` is read
- **THEN** it contains a section titled "Known Limitations" or "已知限制"

#### Scenario: Three root causes are documented

- **WHEN** the known limitations section is read
- **THEN** it explains fuzzy inputs, contradictory conditions, and non-Chinese multilingual behavior as distinct categories with root-cause explanation

<!-- @trace
source: eval-framework
updated: 2026-04-22
code:
  - uv.lock
  - src/ghibli/cli.py
  - evals/queries.yaml
  - .env.example
  - pyproject.toml
  - evals/results.json
  - evals/run_evals.py
  - src/ghibli/github_api.py
  - src/ghibli/agent.py
  - README.md
  - evals/__init__.py
tests:
  - tests/unit/test_eval_runner.py
  - tests/unit/test_eval_queries.py
-->