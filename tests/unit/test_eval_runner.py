import json
from unittest.mock import patch

from ghibli.exceptions import ToolCallError


SAMPLE_ENTRY = {
    "id": "fuzzy-001",
    "category": "fuzzy",
    "query": "找個好用的前端框架",
    "expected_behavior": "calls search_repositories",
    "difficulty": "hard",
    "notes": "test entry",
}


def test_run_single_query_pass():
    from evals.run_evals import run_query

    with patch("evals.run_evals.agent.chat", return_value="Found repos"):
        with patch("evals.run_evals.ghibli.tools.search_repositories") as mock_tool:
            mock_tool.return_value = []
            result = run_query(SAMPLE_ENTRY, session_id="test-session")

    assert result["status"] == "pass"
    assert result["response_preview"] == "Found repos"


def test_run_single_query_error():
    from evals.run_evals import run_query

    with patch("evals.run_evals.agent.chat", side_effect=ToolCallError("boom")):
        result = run_query(SAMPLE_ENTRY, session_id="test-session")

    assert result["status"] == "error"
    assert result["error_message"] == "boom"
    assert result["tools_called"] == []


def test_run_single_query_fail():
    from evals.run_evals import run_query

    with patch("evals.run_evals.agent.chat", return_value=""):
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
