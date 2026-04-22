"""Compare model eval results and output a Markdown accuracy table."""

from __future__ import annotations

import json
from pathlib import Path


_CATEGORIES = ["qualifier", "temporal", "typo", "contradiction", "multi_step", "tool_selection"]


def _latest_run_per_model(runs: list[dict]) -> dict[str, dict]:
    """Return the most recent run for each model, keyed by model name."""
    latest: dict[str, dict] = {}
    for run in runs:
        model = run.get("model", "unknown")
        if model not in latest or run["run_id"] > latest[model]["run_id"]:
            latest[model] = run
    return latest


def _category_accuracy(results: list[dict], category: str) -> str:
    cat_results = [r for r in results if r.get("category") == category]
    if not cat_results:
        return "N/A"
    passed = sum(
        1 for r in cat_results
        if r.get("judge_result") and r["judge_result"].get("pass_")
    )
    return f"{passed / len(cat_results) * 100:.1f}%"


def generate_report(runs: list[dict]) -> str:
    """Generate a Markdown table comparing model accuracies from run data.

    Args:
        runs: List of run_obj dicts (as written by run_evals.py).

    Returns:
        Markdown-formatted comparison table string.
    """
    latest = {m: r for m, r in _latest_run_per_model(runs).items() if m != "unknown"}
    if not latest:
        return "_No eval runs found._\n"

    header = "| Model | Overall | Qualifier | Temporal | Typo | Contradiction | Multi-Step | Tool Selection |"
    separator = "| ----- | ------- | --------- | -------- | ---- | ------------- | ---------- | -------------- |"
    rows = [header, separator]

    for model in sorted(latest.keys()):
        run = latest[model]
        overall = f"{run.get('accuracy', 0.0) * 100:.1f}%"
        results = run.get("results", [])
        qualifier = _category_accuracy(results, "qualifier")
        temporal = _category_accuracy(results, "temporal")
        typo = _category_accuracy(results, "typo")
        contradiction = _category_accuracy(results, "contradiction")
        multi_step = _category_accuracy(results, "multi_step")
        tool_selection = _category_accuracy(results, "tool_selection")
        rows.append(f"| {model} | {overall} | {qualifier} | {temporal} | {typo} | {contradiction} | {multi_step} | {tool_selection} |")

    return "\n".join(rows) + "\n"


def _categories_present(results: list[dict]) -> list[str]:
    seen = {r.get("category") for r in results}
    return [c for c in _CATEGORIES if c in seen]


def main() -> None:
    results_path = Path(__file__).parent / "results.json"
    if not results_path.exists():
        print("No results.json found. Run `uv run python evals/run_evals.py` first.")
        return
    runs: list[dict] = json.loads(results_path.read_text(encoding="utf-8"))
    print(generate_report(runs))


if __name__ == "__main__":
    main()
