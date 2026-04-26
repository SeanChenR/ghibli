"""Compare model tool calls against ground truth to determine pass/fail."""

from __future__ import annotations

import re
from collections import Counter

_ASCII_WORD = re.compile(r"^[a-zA-Z0-9_.\-]+$")


def _keyword_in_text(keyword: str, text_lower: str) -> bool:
    """Case-insensitive keyword search.

    For purely ASCII keywords (e.g. "npm", "pnpm", "get_repository"), use word
    boundaries to avoid false positives like "npm" matching inside "pnpm".
    For keywords containing spaces or non-ASCII characters (e.g. "package
    manager", Chinese terms), fall back to substring match.
    """
    kw_lower = keyword.lower()
    if _ASCII_WORD.match(kw_lower):
        pattern = r"(?<![a-zA-Z0-9_])" + re.escape(kw_lower) + r"(?![a-zA-Z0-9_])"
        return bool(re.search(pattern, text_lower))
    return kw_lower in text_lower


def _is_multiset_subset(required: list[str], actual: list[str]) -> bool:
    """Return True if every tool in `required` appears in `actual` at least as many times.

    Order is ignored. What matters is that the model called each required tool
    the correct number of times. This fits the eval philosophy: we grade whether
    the right tools were used, not the exact ordering — order dependencies are
    typically enforced by data flow (e.g., search before get_repository is
    forced because get_repository needs search's output).
    """
    req = Counter(required)
    act = Counter(actual)
    return all(act[t] >= n for t, n in req.items())


def _content_match(response_text: str, ground_truth: dict) -> bool:
    """Check whether response_text satisfies the content requirements in ground_truth.

    For divergent queries (Type B), multiple tool-call paths can yield a correct
    answer — grading by tool sequence alone is not enough. We also verify the
    model's reply actually contains substantive facts by looking for keywords:

    - `required_content_all`: every listed keyword MUST appear in response_text.
      Example: for a bun/pnpm/npm comparison, require all three names present.
    - `required_content_any_of`: a list of groups; within each group, at least
      one keyword must match. Example: [["package manager", "dependency"]]
      means the reply must talk about package managers or dependencies.

    Matching is case-insensitive substring matching (same philosophy as
    refuse_keywords for refuse scenarios).

    If neither field is set, returns True (no constraint).
    """
    text = response_text.lower()
    for kw in ground_truth.get("required_content_all", []):
        if not _keyword_in_text(kw, text):
            return False
    for group in ground_truth.get("required_content_any_of", []):
        if not any(_keyword_in_text(kw, text) for kw in group):
            return False
    return True


def judge(tools_called: list[str], response_text: str, ground_truth: dict) -> dict:
    """Compare tools_called + response_text against ground_truth and return judgment.

    Returns a dict with:
        tool_match (bool): expected tool present in tools_called (N/A for refuse)
        sequence_match (bool): every tool in tool_sequence appears in tools_called
            enough times (multiset subset; order ignored; True if not specified)
        content_match (bool): response_text satisfies required_content_all /
            required_content_any_of (True if no content fields are set)
        flagged_refusal (bool): response_text contains any refusal_keywords (refuse only)
        pass_ (bool): True only when all applicable checks pass
    """
    expected_tool = ground_truth.get("tool", "")

    # Refuse scenario: partial refusal with a valid sub-question.
    # Model must execute the valid part AND explicitly push back on the infeasible part.
    if expected_tool == "refuse":
        valid_seq = ground_truth.get("valid_parts_tool_sequence", [])
        keywords = ground_truth.get("refusal_keywords", [])

        sequence_match = _is_multiset_subset(valid_seq, tools_called) if valid_seq else True
        flagged_refusal = any(
            kw.lower() in response_text.lower() for kw in keywords
        )
        return {
            "tool_match": True,
            "sequence_match": sequence_match,
            "flagged_refusal": flagged_refusal,
            "pass_": sequence_match and flagged_refusal,
        }

    # Legacy "none" sentinel: model should NOT call any tool at all.
    if expected_tool == "none":
        tool_match = len(tools_called) == 0
        return {"tool_match": tool_match, "sequence_match": True, "pass_": tool_match}

    # Normal case: expected tool present + optional sequence check + optional content check.
    tool_match = expected_tool in tools_called
    tool_sequence = ground_truth.get("tool_sequence")

    if tool_sequence:
        sequence_match = _is_multiset_subset(tool_sequence, tools_called)
    else:
        sequence_match = True

    content_match = _content_match(response_text, ground_truth)

    pass_ = tool_match and sequence_match and content_match
    return {
        "tool_match": tool_match,
        "sequence_match": sequence_match,
        "content_match": content_match,
        "pass_": pass_,
    }
