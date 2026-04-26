from pathlib import Path

import yaml

QUERIES_PATH = Path(__file__).parent.parent.parent / "evals" / "queries.yaml"

VALID_CATEGORIES = {
    "discover",
    "compare",
    "debug_hunt",
    "track_vuln",
    "follow_up",
    "refuse",
}
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
    "none",    # legacy sentinel: model should explain without calling any tool
    "refuse",  # refuse scenario: partial refusal with valid_parts_tool_sequence + refusal_keywords
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


def test_refuse_entries_have_required_refuse_fields():
    data = yaml.safe_load(QUERIES_PATH.read_text(encoding="utf-8"))
    refuse_entries = [e for e in data if e["category"] == "refuse"]
    assert len(refuse_entries) >= 5, "refuse category should have at least 5 entries"
    for entry in refuse_entries:
        gt = entry["ground_truth"]
        assert gt["tool"] == "refuse", (
            f"refuse entry '{entry.get('id')}' ground_truth.tool must be 'refuse'"
        )
        assert "valid_parts_tool_sequence" in gt, (
            f"refuse entry '{entry.get('id')}' missing 'valid_parts_tool_sequence'"
        )
        assert "refusal_keywords" in gt, (
            f"refuse entry '{entry.get('id')}' missing 'refusal_keywords'"
        )
        assert len(gt["refusal_keywords"]) >= 1, (
            f"refuse entry '{entry.get('id')}' refusal_keywords is empty"
        )


def test_non_refuse_entries_have_tool_sequence():
    # All non-refuse queries must declare a tool_sequence (at least 1 tool).
    # After the GT audit, some debug_hunt/track_vuln queries legitimately require
    # only one tool (e.g. search_issues with repo: qualifier is scoped already),
    # so we no longer require >= 2.
    data = yaml.safe_load(QUERIES_PATH.read_text(encoding="utf-8"))
    for entry in data:
        if entry["category"] == "refuse":
            continue
        gt = entry.get("ground_truth", {})
        assert "tool_sequence" in gt, (
            f"entry '{entry.get('id')}' missing ground_truth.tool_sequence"
        )
        assert len(gt["tool_sequence"]) >= 1, (
            f"entry '{entry.get('id')}' tool_sequence is empty"
        )
