# ground-truth-catalog Specification

## Purpose

TBD - created by archiving change 'multi-model-eval'. Update Purpose after archive.

## Requirements

### Requirement: Every query entry carries a ground_truth annotation

Every entry in `evals/queries.yaml` SHALL include a `ground_truth` object. The `ground_truth` object SHALL contain:
- `tool` (string): the name of the primary GitHub tool the model is expected to call
- `params` (object, optional): partial key-value pairs the tool call arguments must satisfy; string values are checked as substrings, others as equality
- `tool_sequence` (list of strings, optional): for multi-step queries, the ordered list of tool names the model SHALL call

#### Scenario: Single-tool query has ground truth

- **WHEN** a query entry with a single expected tool call is read
- **THEN** its `ground_truth.tool` is one of the six valid tool names: `search_repositories`, `get_repository`, `list_issues`, `list_pull_requests`, `get_user`, `list_releases`

#### Scenario: Multi-step query specifies tool sequence

- **WHEN** a query entry in the `multi_step` category is read
- **THEN** its `ground_truth.tool_sequence` is a non-empty list of valid tool names with length ≥ 2

#### Scenario: Param annotations use valid keys

- **WHEN** `ground_truth.params` is present
- **THEN** its keys are drawn from the known parameter set for the specified tool (e.g., `q`, `owner`, `repo`, `username`, `state`, `per_page`)

#### Scenario: All 30 entries have ground truth

- **WHEN** `evals/queries.yaml` is loaded
- **THEN** every entry has a non-null `ground_truth` field

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