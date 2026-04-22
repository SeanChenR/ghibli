## MODIFIED Requirements

### Requirement: Query catalog defines categorized test cases

The file `evals/queries.yaml` SHALL contain at least 30 test queries organized into five categories: `fuzzy`, `typo`, `contradiction`, `multilingual`, and `multi_step`. Each query entry SHALL include: `id` (string, unique), `category` (one of the five), `query` (the natural language string), `expected_behavior` (human-readable description of expected tool call or model behavior), `difficulty` (`easy`, `medium`, or `hard`), `notes` (explanation of why this case is interesting or hard), and `ground_truth` (object with at minimum a `tool` key specifying the expected tool name).

#### Scenario: Catalog has minimum 30 queries

- **WHEN** `evals/queries.yaml` is loaded
- **THEN** it contains at least 30 entries, at least 5 per category

#### Scenario: Each entry has required fields including ground_truth

- **WHEN** any entry in `evals/queries.yaml` is read
- **THEN** it has non-empty values for `id`, `category`, `query`, `expected_behavior`, `difficulty`, `notes`, and `ground_truth.tool`

#### Scenario: Category values are valid

- **WHEN** any entry's `category` field is read
- **THEN** it is one of: `fuzzy`, `typo`, `contradiction`, `multilingual`, `multi_step`

---

## MODIFIED Requirements

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
