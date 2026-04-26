## ADDED Requirements

### Requirement: Semantic judge layer evaluates stored responses without re-calling APIs

The system SHALL provide a `evals/deepeval_judge.py` module that reads stored eval responses from `evals/results/{model}.json` and applies LLM-as-judge metrics on `response_full` and `tool_calls_detail` without re-invoking GitHub API or the model under test.

#### Scenario: Judge reads stored response and produces semantic verdict

- **WHEN** `deepeval_judge.py` is invoked with `--model gemini-vertex`
- **THEN** the system reads `evals/results/gemini-vertex.json`, extracts `query`, `response_full`, and `tool_calls_detail` for each query, runs four DeepEval metrics, and writes verdicts to `evals/results-deepeval/gemini-vertex.json`

#### Scenario: Judge does not invoke GitHub API or under-test model

- **WHEN** semantic judge runs against any stored result
- **THEN** the system makes zero HTTP calls to `api.github.com` and zero calls to the under-test LLM provider, only calling the configured judge LLM via DeepEval

### Requirement: Four metrics evaluate answer quality dimensions

The system SHALL apply exactly four DeepEval metrics per query: `AnswerRelevancyMetric`, `FaithfulnessMetric`, `HallucinationMetric`, and a `GEval` instance named `Partial Refusal Quality`.

#### Scenario: Non-refuse query receives three metric scores

- **WHEN** judging a query whose `category` is not `refuse`
- **THEN** the system computes `answer_relevancy`, `faithfulness`, and `hallucination` scores, and records `partial_refusal` as `null` with reason `"N/A non-refuse"`

#### Scenario: Refuse query additionally receives partial-refusal score

- **WHEN** judging a query whose `category` is `refuse`
- **THEN** the system computes all four metric scores including `partial_refusal`, where the GEval criteria evaluate whether the response correctly answered valid sub-questions while explicitly refusing contradictory sub-questions

#### Scenario: Hallucination metric uses tool results as ground truth context

- **WHEN** computing `HallucinationMetric` for any query
- **THEN** the system passes `result_preview` strings extracted from `tool_calls_detail` as the `context` parameter, so the judge evaluates fabrication relative to actual tool output rather than judge's own training knowledge

### Requirement: Judge LLM is configurable and decoupled from under-test model

The system SHALL use a separately configured LLM as judge (default: `gemini/gemini-2.5-flash` via `GEMINI_API_KEY`), and SHALL NOT use the same model id as the model being judged.

#### Scenario: Default judge model is Gemini 2.5 Flash regardless of under-test model

- **WHEN** environment variable `DEEPEVAL_JUDGE_MODEL` is unset
- **THEN** all three under-test models (`gemini-vertex`, `gemma4`, `gpt51`) are judged by `gemini/gemini-2.5-flash`

#### Scenario: Judge model can be overridden via env var

- **WHEN** `DEEPEVAL_JUDGE_MODEL=openai/gpt-4o` is set
- **THEN** all metrics use that model id, and the judge model id is recorded in the output JSON's `judge_model` field

### Requirement: Output JSON includes per-query verdicts and aggregate summary

The system SHALL write a structured JSON file per under-test model containing per-query metric scores, a `semantic_pass` boolean, a `judge_disagreement` boolean, and an aggregate `summary` block.

#### Scenario: Output records per-query metric details

- **WHEN** judging completes for one model
- **THEN** the output JSON contains a `results` array with one entry per query, each entry including `query_id`, `structural_pass` (copied from input), `metrics` object with score/passed/reason for each metric, `semantic_pass` boolean (true iff all applicable metrics passed), and `judge_disagreement` boolean (`structural_pass != semantic_pass`)

#### Scenario: Output records aggregate summary

- **WHEN** judging completes
- **THEN** the output JSON contains a `summary` object with integer counts: `structural_pass`, `semantic_pass`, `both_pass`, `structural_only` (structural pass but semantic fail), `semantic_only`, and `both_fail`

### Requirement: Async execution with caching for cost control

The system SHALL run metric evaluations with async concurrency capped at 10 parallel calls and SHALL enable DeepEval cache to avoid redundant judge calls on repeated runs.

#### Scenario: Async config caps concurrency

- **WHEN** the judge runs against 30 queries × 4 metrics = 120 metric calls
- **THEN** the system passes `AsyncConfig(run_async=True, max_concurrent=10)` to `evaluate()`

#### Scenario: Cache enabled prevents duplicate API calls on rerun

- **WHEN** judge is invoked twice on the same stored input
- **THEN** the second invocation reuses cached judge results from `~/.deepeval/.deepeval-cache.json` and makes zero new judge LLM API calls

### Requirement: Metric thresholds are explicit constants

The system SHALL declare metric thresholds as named module-level constants in `evals/deepeval_judge.py`.

#### Scenario: Default thresholds are documented constants

- **WHEN** reading the source of `evals/deepeval_judge.py`
- **THEN** four named constants exist: `ANSWER_RELEVANCY_THRESHOLD = 0.7`, `FAITHFULNESS_THRESHOLD = 0.7`, `HALLUCINATION_THRESHOLD = 0.7`, `PARTIAL_REFUSAL_THRESHOLD = 0.6`
