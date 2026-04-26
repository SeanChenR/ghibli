"""Re-evaluate stored eval results against the current queries.yaml ground truth.

Useful when you tweak `judge.py` or `queries.yaml` ground truth and want to see
the impact without re-running the models (which costs API calls and time).
Reads the latest run from each `evals/results/{model}.json`, re-runs the judge
with whatever `queries.yaml` + `judge.py` currently say, and prints updated
per-model + per-category accuracy.

Usage:
    uv run python -m evals.rejudge
    uv run python -m evals.rejudge --model gpt51
    uv run python -m evals.rejudge --detail          # show failing queries
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
import yaml

from evals.judge import judge


_CATEGORIES = ["discover", "compare", "debug_hunt", "track_vuln", "follow_up", "refuse"]


def _load_queries(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {q["id"]: q for q in data}


def _rejudge_run(run: dict, queries: dict) -> tuple[int, int, dict, list]:
    """Re-judge every result in a run. Returns (passed, total, per_category, failing_rows)."""
    per_cat: dict[str, dict] = {c: {"passed": 0, "total": 0} for c in _CATEGORIES}
    failing: list[dict] = []
    passed = 0
    total = 0
    for r in run["results"]:
        qid = r["query_id"]
        q = queries.get(qid)
        if q is None:
            continue
        gt = q.get("ground_truth", {})
        tools_called = r.get("tools_called", [])
        response_text = r.get("response_full", "") or r.get("response_preview", "")
        j = judge(tools_called, response_text, gt)
        cat = r.get("category", "unknown")
        total += 1
        if cat in per_cat:
            per_cat[cat]["total"] += 1
        if j.get("pass_"):
            passed += 1
            if cat in per_cat:
                per_cat[cat]["passed"] += 1
        else:
            failing.append({
                "query_id": qid,
                "category": cat,
                "tools_called": tools_called,
                "judge_result": j,
                "ground_truth_sequence": gt.get("tool_sequence") or gt.get("valid_parts_tool_sequence"),
            })
    return passed, total, per_cat, failing


def main(
    model: Optional[str] = typer.Option(None, help="Only rejudge this model (nickname); default: all"),
    detail: bool = typer.Option(False, help="Show per-failure details"),
) -> None:
    queries_path = Path(__file__).parent / "queries.yaml"
    results_dir = Path(__file__).parent / "results"
    queries = _load_queries(queries_path)

    files = sorted(results_dir.glob("*.json"))
    if model:
        files = [f for f in files if f.stem == model]
    if not files:
        typer.echo("No results files found.", err=True)
        raise typer.Exit(1)

    for f in files:
        runs = json.loads(f.read_text(encoding="utf-8"))
        if not runs:
            continue
        latest = runs[-1]
        passed, total, per_cat, failing = _rejudge_run(latest, queries)
        stored_acc = latest.get("accuracy", 0.0)
        new_acc = passed / total if total else 0.0

        delta = (new_acc - stored_acc) * 100
        delta_str = f"({delta:+.1f}pp)" if abs(delta) > 0.01 else "(same)"
        typer.echo(
            f"\n=== {f.stem} ===  stored={stored_acc:.1%} → rejudged={new_acc:.1%} {delta_str}  ({passed}/{total})"
        )
        for cat in _CATEGORIES:
            c = per_cat[cat]
            if c["total"]:
                typer.echo(f"  {cat}: {c['passed']}/{c['total']}")

        if detail and failing:
            typer.echo("  --- failing queries ---")
            for row in failing:
                judge_info = ", ".join(f"{k}={v}" for k, v in row["judge_result"].items() if k != "pass_")
                typer.echo(
                    f"  XX {row['query_id']}  gt={row['ground_truth_sequence']} "
                    f"tools={row['tools_called'][:6]} [{judge_info}]"
                )


if __name__ == "__main__":
    typer.run(main)
