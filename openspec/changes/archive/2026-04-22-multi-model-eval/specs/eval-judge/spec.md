## ADDED Requirements

### Requirement: Judge compares tool calls against ground truth

The module `evals/judge.py` SHALL provide a function `judge(tools_called: list[str], ground_truth: dict) -> dict` that returns a judgment dict with three boolean fields: `tool_match`, `param_match`, and `sequence_match`, plus a top-level `pass_` (bool) that is `True` only when all applicable checks pass.

Judgment rules:
- `tool_match`: `ground_truth["tool"]` is present anywhere in `tools_called`
- `param_match`: always `True` when `ground_truth.get("params")` is absent; otherwise verified by the caller's `judge_params` helper (param checking is done by `run_evals.py` using the actual tool call args from the model response)
- `sequence_match`: always `True` when `ground_truth.get("tool_sequence")` is absent; otherwise `tools_called` must contain every tool in `tool_sequence` in the specified order (non-contiguous match is acceptable)

#### Scenario: Correct single-tool call passes

- **WHEN** `tools_called = ["search_repositories"]` and `ground_truth = {"tool": "search_repositories"}`
- **THEN** `judge(...)` returns `{"tool_match": True, "param_match": True, "sequence_match": True, "pass_": True}`

#### Scenario: Wrong tool fails

- **WHEN** `tools_called = ["get_user"]` and `ground_truth = {"tool": "search_repositories"}`
- **THEN** `judge(...)` returns `{"tool_match": False, "pass_": False}`

#### Scenario: Multi-step sequence order is enforced

- **WHEN** `tools_called = ["search_repositories", "list_releases"]` and `ground_truth = {"tool": "list_releases", "tool_sequence": ["search_repositories", "list_releases"]}`
- **THEN** `judge(...)` returns `{"sequence_match": True, "pass_": True}`

#### Scenario: Reversed sequence fails

- **WHEN** `tools_called = ["list_releases", "search_repositories"]` and `ground_truth = {"tool_sequence": ["search_repositories", "list_releases"]}`
- **THEN** `judge(...)` returns `{"sequence_match": False, "pass_": False}`

#### Scenario: Empty tools_called always fails

- **WHEN** `tools_called = []` and `ground_truth` specifies any tool
- **THEN** `judge(...)` returns `{"tool_match": False, "pass_": False}`

---

### Requirement: Run accuracy is computed and stored

Each run object in `results.json` SHALL include an `accuracy` field (float, 0.0–1.0) equal to the number of `pass` entries divided by the total number of entries in that run, and a `model` field (string) naming the model used.

#### Scenario: Perfect run has accuracy 1.0

- **WHEN** all 30 queries return `pass` in a run
- **THEN** `run_obj["accuracy"]` equals `1.0`

#### Scenario: Partial accuracy is computed correctly

- **WHEN** 27 out of 30 queries pass
- **THEN** `run_obj["accuracy"]` equals `0.9`

#### Scenario: Per-query result carries judge detail

- **WHEN** a per-query result is read from `results.json`
- **THEN** it contains a `judge_result` object with `tool_match`, `sequence_match`, and `pass_` fields

---

### Requirement: compare_models.py outputs a cross-model accuracy table

The script `evals/compare_models.py` SHALL read `evals/results.json` and print a Markdown table to stdout. The table SHALL have one row per model (using the most recent run for each model) and columns for `Overall`, `fuzzy`, `typo`, `contradiction`, `multilingual`, and `multi_step` accuracy as percentages.

#### Scenario: Table contains all three models when all have been run

- **WHEN** `results.json` contains at least one run for each of `gemini`, `gpt4o-mini`, and `llama3`
- **THEN** the output table contains exactly three data rows plus a header row

#### Scenario: Missing model shows placeholder

- **WHEN** `results.json` has no runs for `llama3`
- **THEN** the `llama3` row is absent from the table (not shown as empty)

#### Scenario: Percentages are rounded to nearest integer

- **WHEN** a model's overall accuracy is 0.8666...
- **THEN** the table shows `87%` for that model's Overall column
