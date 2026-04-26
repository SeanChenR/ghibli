from evals.judge import judge


def test_correct_single_tool_passes():
    result = judge(
        ["search_repositories"],
        "Found some repos.",
        {"tool": "search_repositories"},
    )
    assert result["tool_match"] is True
    assert result["sequence_match"] is True
    assert result["pass_"] is True


def test_wrong_tool_fails():
    result = judge(
        ["get_user"],
        "Fetched user.",
        {"tool": "search_repositories"},
    )
    assert result["tool_match"] is False
    assert result["pass_"] is False


def test_correct_sequence_passes():
    result = judge(
        ["search_repositories", "list_releases"],
        "Here are the releases.",
        {"tool": "list_releases", "tool_sequence": ["search_repositories", "list_releases"]},
    )
    assert result["sequence_match"] is True
    assert result["pass_"] is True


def test_reversed_sequence_now_passes_under_multiset():
    # Under the multiset semantics, order of tool calls is ignored as long as
    # each required tool was called enough times. Data-flow dependencies
    # (e.g. needing search before get_repository) are naturally enforced by
    # the model, not by the judge.
    result = judge(
        ["list_releases", "search_repositories"],
        "Some output.",
        {"tool": "list_releases", "tool_sequence": ["search_repositories", "list_releases"]},
    )
    assert result["sequence_match"] is True
    assert result["pass_"] is True


def test_missing_required_tool_fails():
    # Multiset still catches models that skip a required tool entirely.
    result = judge(
        ["search_repositories"],
        "Only searched.",
        {"tool": "list_releases", "tool_sequence": ["search_repositories", "list_releases"]},
    )
    assert result["sequence_match"] is False
    assert result["pass_"] is False


def test_insufficient_tool_count_fails():
    # Multiset counts multiplicity — 3-way compare requires 3 get_repository calls.
    result = judge(
        ["search_repositories", "get_repository", "get_repository"],
        "Compared two.",
        {"tool": "get_repository", "tool_sequence": ["get_repository", "get_repository", "get_repository"]},
    )
    assert result["sequence_match"] is False
    assert result["pass_"] is False


def test_empty_tools_called_fails():
    result = judge([], "No search was performed.", {"tool": "search_repositories"})
    assert result["tool_match"] is False
    assert result["pass_"] is False


def test_none_sentinel_passes_when_no_tools_called():
    result = judge([], "This request is impossible.", {"tool": "none"})
    assert result["tool_match"] is True
    assert result["pass_"] is True


def test_none_sentinel_fails_when_tool_was_called():
    result = judge(["search_repositories"], "Searched anyway.", {"tool": "none"})
    assert result["tool_match"] is False
    assert result["pass_"] is False


def test_non_contiguous_sequence_passes():
    # Extra tool in between is acceptable
    result = judge(
        ["get_user", "get_repository", "list_issues"],
        "Output.",
        {"tool": "list_issues", "tool_sequence": ["get_user", "list_issues"]},
    )
    assert result["sequence_match"] is True
    assert result["pass_"] is True


# ---------------------------------------------------------------------------
# refuse scenario: partial refusal judging
# ---------------------------------------------------------------------------


_REFUSE_GROUND_TRUTH = {
    "tool": "refuse",
    "valid_parts_tool_sequence": ["search_repositories"],
    "refusal_keywords": ["不可能", "impossible", "no repo"],
}


def test_refuse_passes_when_valid_part_executed_and_refusal_flagged():
    result = judge(
        ["search_repositories"],
        "我幫你搜了 MIT Rust 工具，但 fork 超過 star 1000 倍是不可能的。",
        _REFUSE_GROUND_TRUTH,
    )
    assert result["sequence_match"] is True
    assert result["flagged_refusal"] is True
    assert result["pass_"] is True


def test_refuse_fails_when_valid_part_missing():
    # Model refused everything without doing the valid search
    result = judge(
        [],
        "這個請求不可能，我無法處理。",
        _REFUSE_GROUND_TRUTH,
    )
    assert result["sequence_match"] is False
    assert result["flagged_refusal"] is True
    assert result["pass_"] is False


def test_refuse_fails_when_refusal_not_flagged():
    # Model did the valid search but silently ignored the impossible part
    result = judge(
        ["search_repositories"],
        "這是 MIT Rust 工具的清單。",
        _REFUSE_GROUND_TRUTH,
    )
    assert result["sequence_match"] is True
    assert result["flagged_refusal"] is False
    assert result["pass_"] is False


def test_refuse_keyword_match_is_case_insensitive():
    result = judge(
        ["search_repositories"],
        "Here are the tools. The other part is IMPOSSIBLE to satisfy.",
        _REFUSE_GROUND_TRUTH,
    )
    assert result["flagged_refusal"] is True
    assert result["pass_"] is True


def test_refuse_with_no_valid_parts_only_checks_refusal_keyword():
    # If valid_parts_tool_sequence is empty, sequence_match defaults to True
    ground_truth = {
        "tool": "refuse",
        "valid_parts_tool_sequence": [],
        "refusal_keywords": ["不可能"],
    }
    result = judge([], "這完全不可能。", ground_truth)
    assert result["sequence_match"] is True
    assert result["flagged_refusal"] is True
    assert result["pass_"] is True


# ---------------------------------------------------------------------------
# Content validation (Type B divergent queries)
# ---------------------------------------------------------------------------


def test_content_all_keywords_present_passes():
    result = judge(
        ["search_repositories", "get_readme"],
        "bun is fast, pnpm is disk-efficient, npm is the default.",
        {
            "tool": "get_readme",
            "tool_sequence": ["search_repositories", "get_readme"],
            "required_content_all": ["bun", "pnpm", "npm"],
        },
    )
    assert result["content_match"] is True
    assert result["pass_"] is True


def test_content_all_missing_keyword_fails():
    result = judge(
        ["search_repositories", "get_readme"],
        "bun is fast, pnpm is disk-efficient.",  # no "npm"
        {
            "tool": "get_readme",
            "tool_sequence": ["search_repositories", "get_readme"],
            "required_content_all": ["bun", "pnpm", "npm"],
        },
    )
    assert result["content_match"] is False
    assert result["pass_"] is False


def test_content_any_of_one_group_match_passes():
    result = judge(
        ["search_repositories", "get_readme"],
        "pnpm is a fast package manager.",
        {
            "tool": "get_readme",
            "tool_sequence": ["search_repositories", "get_readme"],
            "required_content_any_of": [["package manager", "dependency"]],
        },
    )
    assert result["content_match"] is True
    assert result["pass_"] is True


def test_content_any_of_all_groups_missing_fails():
    result = judge(
        ["search_repositories", "get_readme"],
        "it is fast.",
        {
            "tool": "get_readme",
            "tool_sequence": ["search_repositories", "get_readme"],
            "required_content_any_of": [["package manager", "dependency"]],
        },
    )
    assert result["content_match"] is False


def test_content_validation_is_case_insensitive():
    result = judge(
        ["search_repositories", "get_readme"],
        "BUN, PNPM, AND NPM are all node tooling.",
        {
            "tool": "get_readme",
            "tool_sequence": ["search_repositories", "get_readme"],
            "required_content_all": ["bun", "pnpm", "npm"],
        },
    )
    assert result["content_match"] is True


def test_no_content_fields_means_no_constraint():
    result = judge(
        ["search_repositories"],
        "whatever",
        {"tool": "search_repositories"},
    )
    # content_match defaults to True when neither required_content_* is set
    assert result["content_match"] is True
    assert result["pass_"] is True


def test_refuse_with_extra_tool_calls_beyond_valid_sequence_still_passes():
    # Subsequence judge: extra tools in between are acceptable
    result = judge(
        ["search_repositories", "get_repository"],
        "搜尋結果如下；但 fork 超 1000 倍 is impossible。",
        _REFUSE_GROUND_TRUTH,
    )
    assert result["sequence_match"] is True
    assert result["flagged_refusal"] is True
    assert result["pass_"] is True
