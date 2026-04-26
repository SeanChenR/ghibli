import json
from unittest.mock import patch

import typer
from typer.testing import CliRunner

from ghibli.exceptions import ToolCallError


SAMPLE_ENTRY = {
    "id": "fuzzy-001",
    "category": "fuzzy",
    "query": "找個好用的前端框架",
    "expected_behavior": "calls search_repositories",
    "difficulty": "hard",
    "notes": "test entry",
    "ground_truth": {"tool": "search_repositories"},
}


def _make_pass_query_result() -> dict:
    return {
        "query_id": "fuzzy-001",
        "category": "fuzzy",
        "status": "pass",
        "judge_result": {"pass_": True, "tool_match": True, "sequence_match": True},
        "tools_called": ["search_repositories"],
        "response_preview": "Found repos",
        "response_full": "Found repos",
        "error_message": None,
        "duration_seconds": 0.1,
    }


def _make_app():
    from evals import run_evals
    app = typer.Typer()
    app.command()(run_evals.main)
    return app, CliRunner()


_FAKE_TOOL_DETAIL = [
    {"tool": "search_repositories", "args": {"q": "test"}, "result_preview": "..."}
]


def test_run_single_query_pass():
    from evals.run_evals import run_query

    with patch(
        "evals.run_evals.chat_with_model",
        return_value=("Found repos", _FAKE_TOOL_DETAIL),
    ):
        result = run_query(SAMPLE_ENTRY, session_id="test-session")

    assert result["status"] == "pass"
    assert result["response_preview"] == "Found repos"
    assert result["tools_called"] == ["search_repositories"]
    assert result["tool_calls_detail"] == _FAKE_TOOL_DETAIL


def test_run_single_query_error():
    from evals.run_evals import run_query

    with patch("evals.run_evals.chat_with_model", side_effect=ToolCallError("boom")):
        result = run_query(SAMPLE_ENTRY, session_id="test-session")

    assert result["status"] == "error"
    assert result["error_message"] == "boom"
    assert result["tools_called"] == []


def test_run_single_query_fail():
    from evals.run_evals import run_query

    with patch("evals.run_evals.chat_with_model", return_value=("", [])):
        result = run_query(SAMPLE_ENTRY, session_id="test-session")

    assert result["status"] == "fail"


def test_results_are_appended(tmp_path):
    from evals.run_evals import append_run

    results_path = str(tmp_path / "results.json")
    run_1 = {"run_id": "2026-01-01T00:00:00", "total": 1, "results": []}
    run_2 = {"run_id": "2026-01-02T00:00:00", "total": 1, "results": []}

    append_run(results_path, run_1)
    append_run(results_path, run_2)

    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) == 2


def test_category_filter():
    from evals.run_evals import filter_queries

    entries = [
        {**SAMPLE_ENTRY, "id": "fuzzy-001", "category": "fuzzy"},
        {**SAMPLE_ENTRY, "id": "typo-001", "category": "typo"},
        {**SAMPLE_ENTRY, "id": "typo-002", "category": "typo"},
    ]

    result = filter_queries(entries, category="typo")

    assert len(result) == 2
    assert all(e["category"] == "typo" for e in result)


# ---------------------------------------------------------------------------
# Task 5.1 TDD-RED: model flag, judge_result, accuracy, unknown model guard
# ---------------------------------------------------------------------------


def test_run_query_result_includes_judge_result():
    """run_query with model_name='gpt5-mini' must return judge_result with pass_."""
    from evals.run_evals import run_query

    with patch(
        "evals.run_evals.chat_with_model",
        return_value=("Found repos", _FAKE_TOOL_DETAIL),
    ):
        result = run_query(SAMPLE_ENTRY, session_id="s1", model_name="gpt5-mini")

    assert "judge_result" in result, "result must contain 'judge_result'"
    assert "pass_" in result["judge_result"], "judge_result must contain 'pass_'"


def test_main_stores_model_in_run_obj():
    """main() --model gemma4 must record model='gemma4' in the run_obj."""
    app, runner = _make_app()
    captured: list[dict] = []

    with patch("evals.run_evals.load_queries", return_value=[SAMPLE_ENTRY]):
        with patch("evals.run_evals.run_query", return_value=_make_pass_query_result()):
            with patch(
                "evals.run_evals.append_run",
                side_effect=lambda _p, r: captured.append(r),
            ):
                result = runner.invoke(app, ["--model", "gemma4"])

    assert result.exit_code == 0, result.output
    assert len(captured) == 1
    assert captured[0]["model"] == "gemma4"


def test_run_accuracy_stored_as_float():
    """run_obj must include an 'accuracy' float (passed judge queries / total)."""
    app, runner = _make_app()
    captured: list[dict] = []

    with patch("evals.run_evals.load_queries", return_value=[SAMPLE_ENTRY]):
        with patch("evals.run_evals.run_query", return_value=_make_pass_query_result()):
            with patch(
                "evals.run_evals.append_run",
                side_effect=lambda _p, r: captured.append(r),
            ):
                runner.invoke(app, ["--model", "gemini"])

    assert len(captured) == 1, "append_run should have been called once"
    assert "accuracy" in captured[0], "run_obj must contain 'accuracy'"
    assert isinstance(captured[0]["accuracy"], float)


def test_unknown_model_does_not_write_results():
    """--model unknown must exit non-zero and never call append_run."""
    app, runner = _make_app()

    with patch("evals.run_evals.load_queries", return_value=[SAMPLE_ENTRY]):
        with patch("evals.run_evals.append_run") as mock_append:
            result = runner.invoke(app, ["--model", "unknown"])

    assert result.exit_code != 0, "unknown model must exit with non-zero code"
    mock_append.assert_not_called()
