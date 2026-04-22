from pathlib import Path

import yaml

QUERIES_PATH = Path(__file__).parent.parent.parent / "evals" / "queries.yaml"

VALID_CATEGORIES = {"qualifier", "temporal", "typo", "contradiction", "multi_step", "tool_selection"}
REQUIRED_FIELDS = {"id", "category", "query", "expected_behavior", "difficulty", "notes"}
VALID_TOOL_NAMES = {
    "search_repositories",
    "get_repository",
    "list_issues",
    "list_pull_requests",
    "get_user",
    "list_releases",
    "get_languages",
    "list_contributors",
    "list_commits",
    "search_code",
    "search_users",
    "search_issues",
    "get_readme",
    "none",  # sentinel: model should explain without calling any tool
}


def test_queries_yaml_loads_without_error():
    data = yaml.safe_load(QUERIES_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert len(data) >= 30


def test_each_query_has_required_fields():
    data = yaml.safe_load(QUERIES_PATH.read_text(encoding="utf-8"))
    for entry in data:
        for field in REQUIRED_FIELDS:
            assert field in entry, f"Missing field '{field}' in entry: {entry.get('id')}"
            assert entry[field], f"Empty field '{field}' in entry: {entry.get('id')}"


def test_category_values_are_valid():
    data = yaml.safe_load(QUERIES_PATH.read_text(encoding="utf-8"))
    for entry in data:
        assert entry["category"] in VALID_CATEGORIES, (
            f"Invalid category '{entry['category']}' in entry: {entry.get('id')}"
        )
    counts = {cat: sum(1 for e in data if e["category"] == cat) for cat in VALID_CATEGORIES}
    for cat, count in counts.items():
        assert count >= 5, f"Category '{cat}' has only {count} entries (need >= 5)"


def test_every_query_entry_carries_ground_truth_annotation():
    data = yaml.safe_load(QUERIES_PATH.read_text(encoding="utf-8"))
    for entry in data:
        assert "ground_truth" in entry, (
            f"Entry '{entry.get('id')}' missing ground_truth field"
        )
        gt = entry["ground_truth"]
        assert "tool" in gt, f"Entry '{entry.get('id')}' ground_truth missing 'tool'"
        assert gt["tool"] in VALID_TOOL_NAMES, (
            f"Entry '{entry.get('id')}' ground_truth.tool '{gt['tool']}' not valid"
        )


def test_multi_step_entries_have_tool_sequence():
    data = yaml.safe_load(QUERIES_PATH.read_text(encoding="utf-8"))
    for entry in data:
        if entry["category"] == "multi_step":
            gt = entry.get("ground_truth", {})
            assert "tool_sequence" in gt, (
                f"multi_step entry '{entry.get('id')}' missing ground_truth.tool_sequence"
            )
            assert len(gt["tool_sequence"]) >= 2, (
                f"multi_step entry '{entry.get('id')}' tool_sequence has < 2 tools"
            )
