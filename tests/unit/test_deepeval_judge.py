"""Tests for evals.deepeval_judge — semantic judge layer using DeepEval.

Tests mock DeepEval's `evaluate()` to avoid real LLM API calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# --- Fixtures ---


def _make_stored_result(query_id: str, category: str, response: str = "answer", structural_pass: bool = True, tool_calls: list[dict] | None = None) -> dict:
    """Build a single stored result entry mimicking evals/results/{model}.json schema."""
    return {
        "query_id": query_id,
        "category": category,
        "query": f"query text for {query_id}",
        "status": "pass",
        "tools_called": ["search_repositories"],
        "tool_calls_detail": tool_calls or [
            {"tool": "search_repositories", "args": {"q": "x"}, "result_preview": f"preview-{query_id}"},
        ],
        "judge_result": {"tool_match": True, "sequence_match": True, "pass_": structural_pass},
        "response_preview": response[:100],
        "response_full": response,
        "error_message": None,
        "duration_seconds": 1.0,
    }


@pytest.fixture
def stored_results_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a fake evals/results/{model}.json with 30 mixed-category results."""
    results_dir = tmp_path / "evals" / "results"
    results_dir.mkdir(parents=True)

    # 25 non-refuse + 5 refuse to mimic real distribution
    non_refuse_cats = ["discover", "compare", "debug_hunt", "track_vuln", "follow_up"]
    results = []
    for cat in non_refuse_cats:
        for i in range(1, 6):
            results.append(_make_stored_result(f"{cat}-{i:03d}", cat))
    for i in range(1, 6):
        results.append(_make_stored_result(f"refuse-{i:03d}", "refuse"))

    run_obj = {
        "run_id": "2026-04-26T00:00:00+00:00",
        "model": "gemini-vertex",
        "total": 30,
        "passed": 28,
        "failed": 2,
        "errors": 0,
        "accuracy": 0.933,
        "results": results,
    }

    file_path = results_dir / "gemini-vertex.json"
    file_path.write_text(json.dumps([run_obj]), encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    return file_path


# --- Tests ---


def test_read_stored_results_returns_30_results(stored_results_file):
    """read_stored_results SHALL parse evals/results/{model}.json and return the
    latest run's results list with all expected fields."""
    from evals.deepeval_judge import read_stored_results

    results = read_stored_results("gemini-vertex")

    assert len(results) == 30
    # Required fields present per stored schema
    for r in results:
        assert "query_id" in r
        assert "category" in r
        assert "query" in r
        assert "response_full" in r
        assert "tool_calls_detail" in r
        assert "judge_result" in r


def test_read_stored_results_raises_when_file_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Missing file SHALL raise FileNotFoundError."""
    monkeypatch.chdir(tmp_path)
    from evals.deepeval_judge import read_stored_results

    with pytest.raises(FileNotFoundError):
        read_stored_results("nonexistent-model")


def _stub_eval_result_passing(test_cases, metrics):
    """Return a fake EvaluationResult where every metric passes for every test case."""
    from types import SimpleNamespace

    test_results = []
    for _ in test_cases:
        md = [
            SimpleNamespace(name="Answer Relevancy", score=0.9, success=True, reason="ok"),
            SimpleNamespace(name="Faithfulness", score=0.9, success=True, reason="ok"),
            SimpleNamespace(name="Hallucination", score=0.1, success=True, reason="ok"),
        ]
        for m in metrics:
            if type(m).__name__ == "GEval":
                md.append(SimpleNamespace(name="Partial Refusal Quality", score=0.8, success=True, reason="ok"))
                break
        test_results.append(SimpleNamespace(metrics_data=md))
    return SimpleNamespace(test_results=test_results)


def test_judge_model_results_does_not_call_github_or_under_test_model(stored_results_file):
    """judge_model_results SHALL only call the injected evaluate_fn, never invoking
    ghibli.agent (under-test model path) or ghibli.github_api (GitHub HTTP path)."""
    from evals import deepeval_judge

    evaluate_calls = []

    def fake_evaluate(*, test_cases, metrics, **kwargs):
        evaluate_calls.append((test_cases, metrics))
        return _stub_eval_result_passing(test_cases, metrics)

    with patch("ghibli.agent.chat") as mock_agent_chat, \
         patch("ghibli.github_api.execute") as mock_github_execute:
        deepeval_judge.judge_model_results("gemini-vertex", evaluate_fn=fake_evaluate)

    assert mock_agent_chat.call_count == 0, "judge must not invoke under-test LLM"
    assert mock_github_execute.call_count == 0, "judge must not hit GitHub API"
    assert evaluate_calls, "judge must call evaluate_fn"


def test_judge_model_results_processes_all_30_queries(stored_results_file):
    """judge_model_results SHALL build and process one LLMTestCase per stored query."""
    from evals import deepeval_judge

    captured_test_cases = []

    def fake_evaluate(*, test_cases, metrics, **kwargs):
        captured_test_cases.extend(test_cases)
        return _stub_eval_result_passing(test_cases, metrics)

    deepeval_judge.judge_model_results("gemini-vertex", evaluate_fn=fake_evaluate)

    # All 30 queries flow through evaluate (may be split into refuse vs non-refuse calls)
    assert len(captured_test_cases) == 30


# --- Task 2.2: Metric construction ---


def test_build_metrics_non_refuse_returns_three_metrics():
    """Non-refuse categories SHALL produce 3 metrics: AnswerRelevancy, Faithfulness, Hallucination."""
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        FaithfulnessMetric,
        HallucinationMetric,
    )

    from evals.deepeval_judge import build_metrics

    metrics = build_metrics(category="discover", judge_model="gemini/gemini-2.5-flash")

    assert len(metrics) == 3
    metric_types = {type(m) for m in metrics}
    assert AnswerRelevancyMetric in metric_types
    assert FaithfulnessMetric in metric_types
    assert HallucinationMetric in metric_types


def test_build_metrics_refuse_adds_geval_partial_refusal():
    """Refuse category SHALL add a 4th metric: GEval named 'Partial Refusal Quality'."""
    from deepeval.metrics import GEval

    from evals.deepeval_judge import build_metrics

    metrics = build_metrics(category="refuse", judge_model="gemini/gemini-2.5-flash")

    assert len(metrics) == 4
    geval_instances = [m for m in metrics if isinstance(m, GEval)]
    assert len(geval_instances) == 1
    assert geval_instances[0].name == "Partial Refusal Quality"


def test_non_refuse_partial_refusal_record_is_null_with_reason():
    """For non-refuse queries, the output entry SHALL record partial_refusal as null with reason 'N/A non-refuse'."""
    from evals.deepeval_judge import empty_partial_refusal_record

    record = empty_partial_refusal_record()

    assert record["score"] is None
    assert record["passed"] is None
    assert record["reason"] == "N/A non-refuse"


# --- Task 2.3: retrieval_context from tool_calls_detail ---


def test_extract_retrieval_context_returns_result_previews():
    """extract_retrieval_context SHALL return the result_preview strings as a list."""
    from evals.deepeval_judge import extract_retrieval_context

    tool_calls = [
        {"tool": "search_repositories", "args": {"q": "rust"}, "result_preview": "preview-A"},
        {"tool": "get_repository", "args": {"owner": "x", "repo": "y"}, "result_preview": "preview-B"},
    ]

    context = extract_retrieval_context(tool_calls)

    assert context == ["preview-A", "preview-B"]


def test_extract_retrieval_context_skips_empty_previews():
    """Tool calls with empty/missing result_preview SHALL be skipped."""
    from evals.deepeval_judge import extract_retrieval_context

    tool_calls = [
        {"tool": "search_repositories", "args": {}, "result_preview": "ok"},
        {"tool": "search_repositories", "args": {}, "result_preview": ""},
        {"tool": "search_repositories", "args": {}},  # no result_preview key
    ]

    context = extract_retrieval_context(tool_calls)

    assert context == ["ok"]


def test_test_case_for_query_uses_tool_call_previews_as_retrieval_context(stored_results_file):
    """The LLMTestCase built per stored query SHALL set retrieval_context from
    tool_calls_detail's result_preview strings (used by HallucinationMetric)."""
    from evals.deepeval_judge import build_test_case

    stored = {
        "query_id": "track_vuln-001",
        "category": "track_vuln",
        "query": "axios incident?",
        "response_full": "There was a supply chain attack...",
        "tool_calls_detail": [
            {"tool": "search_issues", "args": {}, "result_preview": "axios issue: ..."},
            {"tool": "get_repository", "args": {}, "result_preview": "axios repo metadata"},
        ],
    }

    case = build_test_case(stored)

    assert case.retrieval_context == ["axios issue: ...", "axios repo metadata"]
    # HallucinationMetric uses `context` separately — DeepEval expects the same list
    assert case.context == ["axios issue: ...", "axios repo metadata"]


# --- Task 2.4: Judge model env var resolution ---


def test_get_judge_model_default_is_gemini_2_5_flash(monkeypatch: pytest.MonkeyPatch):
    """Default judge model SHALL be `gemini/gemini-2.5-flash` when env var unset."""
    monkeypatch.delenv("DEEPEVAL_JUDGE_MODEL", raising=False)

    from evals.deepeval_judge import get_judge_model

    assert get_judge_model() == "gemini/gemini-2.5-flash"


def test_get_judge_model_respects_env_var(monkeypatch: pytest.MonkeyPatch):
    """DEEPEVAL_JUDGE_MODEL env var SHALL override the default judge model."""
    monkeypatch.setenv("DEEPEVAL_JUDGE_MODEL", "openai/gpt-4o")

    from evals.deepeval_judge import get_judge_model

    assert get_judge_model() == "openai/gpt-4o"


def test_judge_model_results_records_judge_model_in_output(stored_results_file, monkeypatch: pytest.MonkeyPatch):
    """The output dict SHALL include the resolved judge model id."""
    monkeypatch.setenv("DEEPEVAL_JUDGE_MODEL", "openai/gpt-4o")

    from evals import deepeval_judge

    def fake_evaluate(*, test_cases, metrics, **kwargs):
        return _stub_eval_result_passing(test_cases, metrics)

    output = deepeval_judge.judge_model_results("gemini-vertex", evaluate_fn=fake_evaluate)

    assert output["judge_model"] == "openai/gpt-4o"


# --- Task 2.5: Threshold constants ---


def test_threshold_constants_have_documented_values():
    """Module-level threshold constants SHALL exist with documented default values."""
    from evals import deepeval_judge

    assert deepeval_judge.ANSWER_RELEVANCY_THRESHOLD == 0.7
    assert deepeval_judge.FAITHFULNESS_THRESHOLD == 0.7
    assert deepeval_judge.HALLUCINATION_THRESHOLD == 0.7
    assert deepeval_judge.PARTIAL_REFUSAL_THRESHOLD == 0.6


# --- Task 3.1: Output schema and summary aggregation ---


def _fake_metric_data(name: str, score: float, success: bool, reason: str = "ok"):
    """Build a SimpleNamespace mimicking deepeval MetricData attributes."""
    from types import SimpleNamespace

    return SimpleNamespace(name=name, score=score, success=success, reason=reason)


def _fake_test_result(metrics_data: list):
    from types import SimpleNamespace

    return SimpleNamespace(metrics_data=metrics_data)


def _fake_eval_result(test_results: list):
    from types import SimpleNamespace

    return SimpleNamespace(test_results=test_results)


def test_output_schema_records_per_query_metrics(stored_results_file):
    """Each result entry SHALL include query_id, structural_pass, metrics dict
    (4 sub-records), semantic_pass, judge_disagreement."""
    from evals import deepeval_judge

    # Fake evaluate returns deterministic scores: all 3 base metrics pass
    def fake_evaluate(*, test_cases, metrics, **kwargs):
        results = []
        for _ in test_cases:
            md = [
                _fake_metric_data("Answer Relevancy", 0.9, True),
                _fake_metric_data("Faithfulness", 0.85, True),
                _fake_metric_data("Hallucination", 0.1, True),
            ]
            # Refuse subset gets the GEval metric too
            if any(isinstance(m, _import_geval_class()) for m in metrics):
                md.append(_fake_metric_data("Partial Refusal Quality", 0.8, True))
            results.append(_fake_test_result(md))
        return _fake_eval_result(results)

    output = deepeval_judge.judge_model_results("gemini-vertex", evaluate_fn=fake_evaluate)

    assert "results" in output
    assert len(output["results"]) == 30

    # Take a non-refuse entry — should have 4 metric keys with partial_refusal=null
    non_refuse_entry = next(r for r in output["results"] if not r["query_id"].startswith("refuse"))
    assert set(non_refuse_entry["metrics"].keys()) == {
        "answer_relevancy",
        "faithfulness",
        "hallucination",
        "partial_refusal",
    }
    assert non_refuse_entry["metrics"]["partial_refusal"]["score"] is None
    assert non_refuse_entry["metrics"]["partial_refusal"]["reason"] == "N/A non-refuse"
    # Structural pass copied, all metrics passed → semantic_pass=True, no disagreement
    assert non_refuse_entry["structural_pass"] is True
    assert non_refuse_entry["semantic_pass"] is True
    assert non_refuse_entry["judge_disagreement"] is False

    # Refuse entry — partial_refusal has a real score
    refuse_entry = next(r for r in output["results"] if r["query_id"].startswith("refuse"))
    assert refuse_entry["metrics"]["partial_refusal"]["score"] == 0.8
    assert refuse_entry["metrics"]["partial_refusal"]["passed"] is True


def _import_geval_class():
    from deepeval.metrics import GEval

    return GEval


def test_judge_disagreement_is_true_when_structural_and_semantic_diverge(stored_results_file):
    """When structural_pass != semantic_pass, judge_disagreement SHALL be True."""
    from evals import deepeval_judge

    # All semantic metrics fail → semantic_pass=False; structural_pass copied (True per fixture)
    def fake_evaluate(*, test_cases, metrics, **kwargs):
        results = []
        for _ in test_cases:
            md = [
                _fake_metric_data("Answer Relevancy", 0.3, False),
                _fake_metric_data("Faithfulness", 0.2, False),
                _fake_metric_data("Hallucination", 0.9, False),
            ]
            if any(isinstance(m, _import_geval_class()) for m in metrics):
                md.append(_fake_metric_data("Partial Refusal Quality", 0.2, False))
            results.append(_fake_test_result(md))
        return _fake_eval_result(results)

    output = deepeval_judge.judge_model_results("gemini-vertex", evaluate_fn=fake_evaluate)

    for entry in output["results"]:
        assert entry["structural_pass"] is True  # fixture default
        assert entry["semantic_pass"] is False
        assert entry["judge_disagreement"] is True


def test_evaluate_is_called_with_async_and_cache_config(stored_results_file):
    """evaluate() SHALL be called with AsyncConfig(run_async=True, max_concurrent=10)
    and CacheConfig(use_cache=True, write_cache=True)."""
    from deepeval.evaluate.configs import AsyncConfig, CacheConfig

    from evals import deepeval_judge

    captured_kwargs = []

    def fake_evaluate(*, test_cases, metrics, **kwargs):
        captured_kwargs.append(kwargs)
        return _stub_eval_result_passing(test_cases, metrics)

    deepeval_judge.judge_model_results("gemini-vertex", evaluate_fn=fake_evaluate)

    assert captured_kwargs, "evaluate must have been called"

    for kwargs in captured_kwargs:
        async_cfg = kwargs.get("async_config")
        cache_cfg = kwargs.get("cache_config")
        assert isinstance(async_cfg, AsyncConfig)
        assert async_cfg.run_async is True
        assert async_cfg.max_concurrent == 10
        assert isinstance(cache_cfg, CacheConfig)
        assert cache_cfg.use_cache is True
        assert cache_cfg.write_cache is True


def test_cli_writes_output_to_results_deepeval_directory(stored_results_file, monkeypatch: pytest.MonkeyPatch):
    """CLI invocation SHALL write output JSON to evals/results-deepeval/{model}.json."""
    from typer.testing import CliRunner

    from evals import deepeval_judge

    def fake_evaluate(*, test_cases, metrics, **kwargs):
        return _stub_eval_result_passing(test_cases, metrics)

    monkeypatch.setattr(deepeval_judge, "_default_evaluate", fake_evaluate, raising=False)

    runner = CliRunner()
    result = runner.invoke(deepeval_judge.app, ["--model", "gemini-vertex"])

    assert result.exit_code == 0, result.output

    output_path = Path("evals") / "results-deepeval" / "gemini-vertex.json"
    assert output_path.exists()
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["model"] == "gemini-vertex"
    assert len(output["results"]) == 30


def test_cli_unknown_model_exits_nonzero(stored_results_file):
    """CLI SHALL exit non-zero when stored results file is missing for the named model."""
    from typer.testing import CliRunner

    from evals import deepeval_judge

    runner = CliRunner()
    result = runner.invoke(deepeval_judge.app, ["--model", "nonexistent-model"])

    assert result.exit_code != 0


def test_summary_counts_match_six_required_buckets(stored_results_file):
    """Summary SHALL contain six integer counts matching disagreement buckets."""
    from evals import deepeval_judge

    # All semantic pass; structural also pass (fixture default)
    def fake_evaluate(*, test_cases, metrics, **kwargs):
        results = []
        for _ in test_cases:
            md = [
                _fake_metric_data("Answer Relevancy", 0.9, True),
                _fake_metric_data("Faithfulness", 0.9, True),
                _fake_metric_data("Hallucination", 0.1, True),
            ]
            if any(isinstance(m, _import_geval_class()) for m in metrics):
                md.append(_fake_metric_data("Partial Refusal Quality", 0.9, True))
            results.append(_fake_test_result(md))
        return _fake_eval_result(results)

    output = deepeval_judge.judge_model_results("gemini-vertex", evaluate_fn=fake_evaluate)

    summary = output["summary"]
    expected_keys = {
        "structural_pass",
        "semantic_pass",
        "both_pass",
        "structural_only",
        "semantic_only",
        "both_fail",
    }
    assert set(summary.keys()) == expected_keys
    for v in summary.values():
        assert isinstance(v, int)

    # All 30 pass both judges
    assert summary["both_pass"] == 30
    assert summary["structural_only"] == 0
    assert summary["semantic_only"] == 0
    assert summary["both_fail"] == 0
    assert summary["structural_pass"] == 30
    assert summary["semantic_pass"] == 30
