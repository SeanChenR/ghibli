from evals.tool_schema import get_openai_tool_schemas

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
}


def test_get_openai_tool_schemas_returns_thirteen_tools():
    schemas = get_openai_tool_schemas()
    assert len(schemas) == 13


def test_each_schema_has_openai_structure():
    schemas = get_openai_tool_schemas()
    for schema in schemas:
        assert schema["type"] == "function"
        fn = schema["function"]
        assert "name" in fn and isinstance(fn["name"], str)
        assert "description" in fn and isinstance(fn["description"], str)
        assert "parameters" in fn and isinstance(fn["parameters"], dict)


def test_schema_names_match_all_tools():
    schemas = get_openai_tool_schemas()
    names = {s["function"]["name"] for s in schemas}
    assert names == VALID_TOOL_NAMES


def test_parameters_is_json_schema_object():
    schemas = get_openai_tool_schemas()
    for schema in schemas:
        params = schema["function"]["parameters"]
        assert params.get("type") == "object"
        assert "properties" in params
