from pathlib import Path

import yaml

QUERIES_PATH = Path(__file__).parent.parent.parent / "evals" / "queries.yaml"

VALID_CATEGORIES = {"fuzzy", "typo", "contradiction", "multilingual", "multi_step"}
REQUIRED_FIELDS = {"id", "category", "query", "expected_behavior", "difficulty", "notes"}


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
