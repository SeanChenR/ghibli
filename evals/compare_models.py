"""Compare model eval results and output a Markdown accuracy table."""

from __future__ import annotations

import json
from pathlib import Path


_CATEGORIES = [
    "discover",
    "compare",
    "debug_hunt",
    "track_vuln",
    "follow_up",
    "refuse",
]


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

    category_headers = [c.replace("_", " ").title() for c in _CATEGORIES]
    header_cells = ["Model", "Overall"] + category_headers
    separator_cells = ["-" * len(c) for c in header_cells]
    rows = [
        "| " + " | ".join(header_cells) + " |",
        "| " + " | ".join(separator_cells) + " |",
    ]

    for model in sorted(latest.keys()):
        run = latest[model]
        overall = f"{run.get('accuracy', 0.0) * 100:.1f}%"
        results = run.get("results", [])
        cells = [model, overall] + [_category_accuracy(results, c) for c in _CATEGORIES]
        rows.append("| " + " | ".join(cells) + " |")

    return "\n".join(rows) + "\n"


def _load_all_runs(results_dir: Path) -> list[dict]:
    """Load and flatten runs from every per-model JSON file in results_dir."""
    all_runs: list[dict] = []
    for path in sorted(results_dir.glob("*.json")):
        file_runs = json.loads(path.read_text(encoding="utf-8"))
        all_runs.extend(file_runs)
    return all_runs


def main() -> None:
    results_dir = Path(__file__).parent / "results"
    if not results_dir.exists() or not any(results_dir.glob("*.json")):
        print(
            "No results found in evals/results/. "
            "Run `uv run python evals/run_evals.py --model <name>` first."
        )
        return
    runs = _load_all_runs(results_dir)
    print(generate_report(runs))


if __name__ == "__main__":
    main()
