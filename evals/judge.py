"""Compare model tool calls against ground truth to determine pass/fail."""

from __future__ import annotations


def _is_subsequence(sequence: list[str], tools: list[str]) -> bool:
    """Return True if sequence appears in tools in order (non-contiguous ok)."""
    it = iter(tools)
    return all(tool in it for tool in sequence)


def judge(tools_called: list[str], ground_truth: dict) -> dict:
    """Compare tools_called against ground_truth and return judgment.

    Returns a dict with:
        tool_match (bool): expected tool present in tools_called
        sequence_match (bool): tool_sequence order satisfied (True if not specified)
        pass_ (bool): True only when all applicable checks pass
    """
    expected_tool = ground_truth.get("tool", "")
    tool_sequence = ground_truth.get("tool_sequence")

    # Sentinel: "none" means the model should NOT call any tool
    if expected_tool == "none":
        tool_match = len(tools_called) == 0
        return {"tool_match": tool_match, "sequence_match": True, "pass_": tool_match}

    tool_match = expected_tool in tools_called

    if tool_sequence:
        sequence_match = _is_subsequence(tool_sequence, tools_called)
    else:
        sequence_match = True

    pass_ = tool_match and sequence_match
    return {"tool_match": tool_match, "sequence_match": sequence_match, "pass_": pass_}
