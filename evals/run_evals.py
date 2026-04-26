"""Eval runner: execute queries against the real ghibli agent and record results."""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
import yaml
from dotenv import load_dotenv

from evals.judge import judge
from evals.models import chat_with_model
from ghibli.exceptions import GhibliError, ToolCallError

load_dotenv(override=True)

_VALID_MODELS = {"gemini", "gemini-vertex", "gemini-vertex-pro", "gemma4", "gpt4o", "gpt5-mini", "gpt51", "ollama-cloud"}


def load_queries(path: str) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def filter_queries(
    queries: list[dict],
    category: str | None,
    query_ids: list[str] | None = None,
) -> list[dict]:
    if query_ids:
        id_set = set(query_ids)
        return [q for q in queries if q["id"] in id_set]
    if category is None:
        return queries
    return [q for q in queries if q["category"] == category]


def run_query(entry: dict, session_id: str, model_name: str = "gemini") -> dict:
    tool_calls_detail: list[dict] = []
    ground_truth = entry.get("ground_truth", {})

    start = time.perf_counter()
    try:
        # All models use chat_with_model (LiteLLM) for consistent tool recording.
        # The native agent.chat path doesn't expose tool call interception reliably.
        response, tool_calls_detail = chat_with_model(entry["query"], session_id, model_name)
    except (GhibliError, ToolCallError) as e:
        duration = round(time.perf_counter() - start, 3)
        tools_called = [d["tool"] for d in tool_calls_detail]
        return {
            "query_id": entry["id"],
            "category": entry["category"],
            "query": entry["query"],
            "status": "error",
            "tools_called": tools_called,
            "tool_calls_detail": tool_calls_detail,
            "judge_result": judge(tools_called, "", ground_truth) if ground_truth else None,
            "response_preview": "",
            "error_message": str(e),
            "duration_seconds": duration,
        }

    duration = round(time.perf_counter() - start, 3)
    status = "pass" if response else "fail"
    response_text = response or ""
    tools_called = [d["tool"] for d in tool_calls_detail]
    return {
        "query_id": entry["id"],
        "category": entry["category"],
        "query": entry["query"],
        "status": status,
        "tools_called": tools_called,
        "tool_calls_detail": tool_calls_detail,
        "judge_result": judge(tools_called, response_text, ground_truth) if ground_truth else None,
        "response_preview": response_text[:200],
        "response_full": response_text,
        "error_message": None,
        "duration_seconds": duration,
    }


def append_run(results_path: str, run: dict) -> None:
    path = Path(results_path)
    if path.exists():
        existing: list = json.loads(path.read_text(encoding="utf-8"))
    else:
        existing = []
    existing.append(run)
    path.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
    )


_CATEGORY_OPTION = typer.Option(None, "--category", help="Filter by category")
_MODEL_OPTION = typer.Option("gemini", "--model", help="Model to evaluate: gemini, gemini-vertex, gemma4, gpt5-mini, ollama-cloud")
_QUERY_IDS_OPTION = typer.Option(
    None,
    "--query-ids",
    help="Comma-separated list of query IDs to run (e.g. 'discover-004,compare-005'). Overrides --category.",
)


def main(
    category: Optional[str] = _CATEGORY_OPTION,
    model: str = _MODEL_OPTION,
    query_ids: Optional[str] = _QUERY_IDS_OPTION,
):
    if model not in _VALID_MODELS:
        valid = ", ".join(sorted(_VALID_MODELS))
        typer.echo(f"Error: unknown model '{model}'. Valid options: {valid}", err=True)
        raise typer.Exit(1)

    queries_path = Path(__file__).parent / "queries.yaml"
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    results_path = results_dir / f"{model}.json"

    all_queries = load_queries(str(queries_path))
    parsed_ids = [q.strip() for q in query_ids.split(",")] if query_ids else None
    queries = filter_queries(all_queries, category, parsed_ids)

    results = []
    passed = failed = errors = 0
    judge_passed = 0

    for entry in queries:
        typer.echo(f"Running {entry['id']}...", nl=False)
        # Fresh session per query prevents context contamination across eval queries
        result = run_query(entry, session_id=str(uuid.uuid4()), model_name=model)
        results.append(result)

        if result["status"] == "pass":
            passed += 1
        elif result["status"] == "fail":
            failed += 1
        else:
            errors += 1

        if result.get("judge_result") and result["judge_result"].get("pass_"):
            judge_passed += 1

        typer.echo(f" {result['status']}")

    total = len(results)
    accuracy = judge_passed / total if total > 0 else 0.0

    run_obj = {
        "run_id": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "total": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "accuracy": accuracy,
        "results": results,
    }

    append_run(str(results_path), run_obj)

    summary = f"{passed} pass / {failed} fail / {errors} error (total {total})"
    typer.echo(f"\nSummary: {summary}")
    typer.echo(f"Accuracy (judge): {accuracy:.1%}")
    typer.echo(f"Results saved to {results_path}")


if __name__ == "__main__":
    typer.run(main)
