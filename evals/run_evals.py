"""Eval runner: execute queries against the real ghibli agent and record results."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import typer
import yaml
from dotenv import load_dotenv

import ghibli.tools
from ghibli import agent
from ghibli.exceptions import GhibliError

load_dotenv(override=True)

_TOOL_NAMES = [
    "search_repositories",
    "get_repository",
    "list_issues",
    "list_pull_requests",
    "get_user",
    "list_releases",
]


def load_queries(path: str) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def filter_queries(queries: list[dict], category: str | None) -> list[dict]:
    if category is None:
        return queries
    return [q for q in queries if q["category"] == category]


def run_query(entry: dict, session_id: str) -> dict:
    tools_called: list[str] = []

    def make_recorder(name: str, original):
        def wrapper(*args, **kwargs):
            tools_called.append(name)
            return original(*args, **kwargs)
        return wrapper

    start = time.perf_counter()
    with ExitStack() as stack:
        for name in _TOOL_NAMES:
            original = getattr(ghibli.tools, name)
            recorder = make_recorder(name, original)
            stack.enter_context(
                patch.object(ghibli.tools, name, side_effect=recorder)
            )
        try:
            response = agent.chat(entry["query"], session_id, False)
        except GhibliError as e:
            duration = round(time.perf_counter() - start, 3)
            return {
                "query_id": entry["id"],
                "category": entry["category"],
                "query": entry["query"],
                "status": "error",
                "tools_called": tools_called,
                "response_preview": "",
                "error_message": str(e),
                "duration_seconds": duration,
            }

    duration = round(time.perf_counter() - start, 3)
    status = "pass" if response else "fail"
    return {
        "query_id": entry["id"],
        "category": entry["category"],
        "query": entry["query"],
        "status": status,
        "tools_called": tools_called,
        "response_preview": (response[:200] if response else ""),
        "response_full": response or "",
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


def main(category: Optional[str] = _CATEGORY_OPTION):
    queries_path = Path(__file__).parent / "queries.yaml"
    results_path = Path(__file__).parent / "results.json"

    all_queries = load_queries(str(queries_path))
    queries = filter_queries(all_queries, category)

    session_id = str(uuid.uuid4())
    results = []
    passed = failed = errors = 0

    for entry in queries:
        typer.echo(f"Running {entry['id']}...", nl=False)
        result = run_query(entry, session_id)
        results.append(result)

        if result["status"] == "pass":
            passed += 1
        elif result["status"] == "fail":
            failed += 1
        else:
            errors += 1

        typer.echo(f" {result['status']}")

    run_obj = {
        "run_id": datetime.now(timezone.utc).isoformat(),
        "total": len(results),
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "results": results,
    }

    append_run(str(results_path), run_obj)

    total = len(results)
    summary = f"{passed} pass / {failed} fail / {errors} error (total {total})"
    typer.echo(f"\nSummary: {summary}")
    typer.echo(f"Results saved to {results_path}")


if __name__ == "__main__":
    typer.run(main)
