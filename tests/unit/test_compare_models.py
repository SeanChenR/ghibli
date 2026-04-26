"""TDD-RED tests for evals.compare_models.generate_report."""

from __future__ import annotations


def _make_run(model: str, accuracy: float, results: list[dict] | None = None) -> dict:
    rows = results or []
    return {
        "run_id": "2026-04-26T00:00:00+00:00",
        "model": model,
        "total": len(rows),
        "passed": sum(1 for r in rows if r.get("status") == "pass"),
        "failed": sum(1 for r in rows if r.get("status") == "fail"),
        "errors": 0,
        "accuracy": accuracy,
        "results": rows,
    }


def _make_result(category: str, pass_: bool) -> dict:
    return {
        "query_id": f"{category}-001",
        "category": category,
        "status": "pass" if pass_ else "fail",
        "judge_result": {"pass_": pass_, "tool_match": pass_, "sequence_match": True},
        "tools_called": [],
        "response_preview": "",
        "response_full": "",
        "error_message": None,
        "duration_seconds": 0.1,
    }


# Three runs with per-category results so category columns can be computed
_GEMINI_RESULTS = [
    _make_result("discover", True),
    _make_result("compare", True),
    _make_result("debug_hunt", True),
    _make_result("track_vuln", False),
    _make_result("follow_up", True),
    _make_result("refuse", True),
]
_GPT4O_RESULTS = [
    _make_result("discover", True),
    _make_result("compare", False),
    _make_result("debug_hunt", True),
    _make_result("track_vuln", True),
    _make_result("follow_up", True),
    _make_result("refuse", True),
]
_LLAMA3_RESULTS = [
    _make_result("discover", False),
    _make_result("compare", True),
    _make_result("debug_hunt", False),
    _make_result("track_vuln", True),
    _make_result("follow_up", True),
    _make_result("refuse", True),
]

THREE_MODEL_RUNS = [
    _make_run("gemini", 0.750, _GEMINI_RESULTS),
    _make_run("gpt5-mini", 0.750, _GPT4O_RESULTS),
    _make_run("llama3", 0.750, _LLAMA3_RESULTS),
]

TWO_MODEL_RUNS = [
    _make_run("gemini", 0.900, _GEMINI_RESULTS),
    _make_run("gpt5-mini", 0.833, _GPT4O_RESULTS),
]


class TestGenerateReport:
    """generate_report() returns a Markdown table with per-model accuracy."""

    def _call(self, runs: list[dict]) -> str:
        from evals.compare_models import generate_report
        return generate_report(runs)

    def test_three_models_produce_three_data_rows(self):
        """With runs from 3 models, output contains a data row for each."""
        output = self._call(THREE_MODEL_RUNS)
        model_rows = [
            line for line in output.splitlines()
            if any(m in line for m in ("gemini", "gpt5-mini", "llama3"))
        ]
        assert len(model_rows) == 3, f"Expected 3 data rows, got {len(model_rows)}:\n{output}"

    def test_accuracy_displayed_as_rounded_percentage(self):
        """Accuracy must appear as a rounded 1-decimal percentage string."""
        runs = [
            _make_run("gemini", 0.9),
            _make_run("gpt5-mini", 0.8333),
        ]
        output = self._call(runs)
        assert "90.0%" in output, f"Expected '90.0%' in output:\n{output}"
        assert "83.3%" in output, f"Expected '83.3%' in output:\n{output}"

    def test_missing_llama3_produces_two_data_rows(self):
        """With only 2 model runs, output must have 2 data rows and no llama3 row."""
        output = self._call(TWO_MODEL_RUNS)
        model_rows = [
            line for line in output.splitlines()
            if any(m in line for m in ("gemini", "gpt5-mini", "llama3"))
        ]
        assert len(model_rows) == 2, f"Expected 2 data rows, got {len(model_rows)}:\n{output}"
        assert "llama3" not in output, "llama3 should not appear when its run is missing"
