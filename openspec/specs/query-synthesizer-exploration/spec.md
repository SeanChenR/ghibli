# query-synthesizer-exploration Specification

## Purpose

TBD - created by archiving change 'deepeval-semantic-judge'. Update Purpose after archive.

## Requirements

### Requirement: Synthesizer exploration generates queries from scratch

The system SHALL provide an `evals/synthesizer_explore.py` script that uses DeepEval `Synthesizer.generate_goldens_from_scratch` to produce a one-time batch of LLM-generated queries scoped to GitHub natural language Q&A.

#### Scenario: Generation parameters constrain scope to GitHub domain

- **WHEN** `synthesizer_explore.py` is invoked
- **THEN** the system calls `generate_goldens_from_scratch` with `subject = "GitHub natural language query about open-source repos, releases, issues, contributors"`, `task = "answer technical questions by searching GitHub"`, and `max_goldens = 15`

#### Scenario: Three evolution types produce five queries each

- **WHEN** the synthesizer runs
- **THEN** the system requests `evolution_types = ["REASONING", "COMPARATIVE", "MULTICONTEXT"]` and produces approximately 5 queries per evolution type, totaling about 15 queries


<!-- @trace
source: deepeval-semantic-judge
updated: 2026-04-26
code:
  - .deepeval/.deepeval-cache.json
  - README.md
  - pyproject.toml
  - .deepeval/.deepeval_telemetry.txt
  - evals/README.md
  - evals/synthesized-queries/findings.md
  - evals/results-deepeval/gemini-vertex.json
  - evals/synthesizer_explore.py
  - .deepeval/.latest_test_run.json
  - evals/results-deepeval/gpt51.json
  - evals/deepeval_judge.py
  - uv.lock
  - evals/results-deepeval/gemma4.json
tests:
  - tests/unit/test_deepeval_judge.py
-->

---
### Requirement: Generated output is preserved for offline review

The system SHALL write generated queries to a timestamped JSON file under `evals/synthesized-queries/` for human inspection.

#### Scenario: Output file uses ISO timestamp

- **WHEN** generation completes
- **THEN** the system writes results to `evals/synthesized-queries/<ISO-timestamp>.json` containing the raw `Golden` objects serialized with their `input`, `expected_output` (if present), and `evolution_type` fields

#### Scenario: Synthesized queries are not loaded by run_evals

- **WHEN** `evals/run_evals.py` runs
- **THEN** the system reads only `evals/queries.yaml` and ignores any files under `evals/synthesized-queries/`


<!-- @trace
source: deepeval-semantic-judge
updated: 2026-04-26
code:
  - .deepeval/.deepeval-cache.json
  - README.md
  - pyproject.toml
  - .deepeval/.deepeval_telemetry.txt
  - evals/README.md
  - evals/synthesized-queries/findings.md
  - evals/results-deepeval/gemini-vertex.json
  - evals/synthesizer_explore.py
  - .deepeval/.latest_test_run.json
  - evals/results-deepeval/gpt51.json
  - evals/deepeval_judge.py
  - uv.lock
  - evals/results-deepeval/gemma4.json
tests:
  - tests/unit/test_deepeval_judge.py
-->

---
### Requirement: Findings document compares synthesized queries against manual set

The system SHALL produce a Markdown findings document at `evals/synthesized-queries/findings.md` that records observations about the synthesized queries' quality relative to the manual 30-query validation set.

#### Scenario: Findings document covers four assessment dimensions

- **WHEN** reading `evals/synthesized-queries/findings.md`
- **THEN** the document contains four explicit sections evaluating: (1) whether generated queries fall within ghibli's GitHub scope, (2) whether language coverage matches the manual set's six non-English languages, (3) whether eval-leakage risk exists (because the same LLM family generated both queries and ground truth), and (4) whether any generated queries are fit to enter the production validation set

#### Scenario: Findings document records concrete examples

- **WHEN** reading the findings document
- **THEN** each of the four assessment sections includes at least two specific generated query examples (verbatim or paraphrased) supporting its conclusion

<!-- @trace
source: deepeval-semantic-judge
updated: 2026-04-26
code:
  - .deepeval/.deepeval-cache.json
  - README.md
  - pyproject.toml
  - .deepeval/.deepeval_telemetry.txt
  - evals/README.md
  - evals/synthesized-queries/findings.md
  - evals/results-deepeval/gemini-vertex.json
  - evals/synthesizer_explore.py
  - .deepeval/.latest_test_run.json
  - evals/results-deepeval/gpt51.json
  - evals/deepeval_judge.py
  - uv.lock
  - evals/results-deepeval/gemma4.json
tests:
  - tests/unit/test_deepeval_judge.py
-->