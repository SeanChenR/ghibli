from evals.judge import judge


def test_correct_single_tool_passes():
    result = judge(
        ["search_repositories"],
        {"tool": "search_repositories"},
    )
    assert result["tool_match"] is True
    assert result["sequence_match"] is True
    assert result["pass_"] is True


def test_wrong_tool_fails():
    result = judge(
        ["get_user"],
        {"tool": "search_repositories"},
    )
    assert result["tool_match"] is False
    assert result["pass_"] is False


def test_correct_sequence_passes():
    result = judge(
        ["search_repositories", "list_releases"],
        {"tool": "list_releases", "tool_sequence": ["search_repositories", "list_releases"]},
    )
    assert result["sequence_match"] is True
    assert result["pass_"] is True


def test_reversed_sequence_fails():
    result = judge(
        ["list_releases", "search_repositories"],
        {"tool": "list_releases", "tool_sequence": ["search_repositories", "list_releases"]},
    )
    assert result["sequence_match"] is False
    assert result["pass_"] is False


def test_empty_tools_called_fails():
    result = judge([], {"tool": "search_repositories"})
    assert result["tool_match"] is False
    assert result["pass_"] is False


def test_none_sentinel_passes_when_no_tools_called():
    result = judge([], {"tool": "none"})
    assert result["tool_match"] is True
    assert result["pass_"] is True


def test_none_sentinel_fails_when_tool_was_called():
    result = judge(["search_repositories"], {"tool": "none"})
    assert result["tool_match"] is False
    assert result["pass_"] is False


def test_non_contiguous_sequence_passes():
    # Extra tool in between is acceptable
    result = judge(
        ["get_user", "get_repository", "list_issues"],
        {"tool": "list_issues", "tool_sequence": ["get_user", "list_issues"]},
    )
    assert result["sequence_match"] is True
    assert result["pass_"] is True
