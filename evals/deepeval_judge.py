"""Semantic judge layer using DeepEval.

Reads stored eval results from `evals/results/{model}.json` and applies LLM-as-judge
metrics on `response_full` and `tool_calls_detail` without re-invoking GitHub API
or the under-test LLM.

The judge LLM defaults to Gemini 2.5 Flash via GEMINI_API_KEY (override with the
DEEPEVAL_JUDGE_MODEL env var). Output is written to
`evals/results-deepeval/{model}.json` containing per-query metric scores plus an
aggregate summary comparing structural vs semantic verdicts.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable

# Module-level metric thresholds (per spec: Metric thresholds are explicit constants)
ANSWER_RELEVANCY_THRESHOLD = 0.7
FAITHFULNESS_THRESHOLD = 0.7
HALLUCINATION_THRESHOLD = 0.7
PARTIAL_REFUSAL_THRESHOLD = 0.6

DEFAULT_JUDGE_MODEL = "gemini/gemini-2.5-flash"

RESULTS_DIR = Path("evals/results")
OUTPUT_DIR = Path("evals/results-deepeval")


def read_stored_results(model_name: str) -> list[dict[str, Any]]:
    """Read `evals/results/{model_name}.json` and return the latest run's results list."""
    path = RESULTS_DIR / f"{model_name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Stored results not found: {path}")
    runs = json.loads(path.read_text(encoding="utf-8"))
    if not runs:
        raise ValueError(f"Empty results file: {path}")
    latest = runs[-1] if isinstance(runs, list) else runs
    return latest.get("results", [])


def get_judge_model() -> str:
    """Resolve the judge LLM model id from env or fall back to the default."""
    return os.environ.get("DEEPEVAL_JUDGE_MODEL", DEFAULT_JUDGE_MODEL)


def _build_judge_llm(model_id: str):
    """Wrap a LiteLLM-style model id (`provider/model`) in the matching DeepEval model class.

    DeepEval metrics need a model *object* — they cannot auto-route a bare provider/model
    string the way LiteLLM does. Returns the original string for unknown prefixes so
    DeepEval's own resolution logic (or a test stub) can take over.
    """
    if model_id.startswith("gemini/"):
        from deepeval.models import GeminiModel

        return GeminiModel(model=model_id.removeprefix("gemini/"))
    if model_id.startswith("openai/"):
        from deepeval.models import GPTModel

        return GPTModel(model=model_id.removeprefix("openai/"))
    if model_id.startswith("anthropic/"):
        from deepeval.models import AnthropicModel

        return AnthropicModel(model=model_id.removeprefix("anthropic/"))
    if model_id.startswith("ollama/"):
        from deepeval.models import OllamaModel

        return OllamaModel(model=model_id.removeprefix("ollama/"))
    return model_id


def empty_partial_refusal_record() -> dict[str, Any]:
    """Sentinel record for non-refuse queries that bypass partial refusal evaluation."""
    return {"score": None, "passed": None, "reason": "N/A non-refuse"}


def extract_retrieval_context(tool_calls_detail: list[dict[str, Any]]) -> list[str]:
    """Pull non-empty `result_preview` strings out of the stored tool call trace.

    Used as both `retrieval_context` and `context` on the LLMTestCase so the
    HallucinationMetric judges fabrication relative to actual tool output rather
    than the judge LLM's training data.
    """
    return [
        tc["result_preview"]
        for tc in tool_calls_detail
        if tc.get("result_preview")
    ]


def build_test_case(stored: dict[str, Any]):
    """Translate one stored result entry into a DeepEval LLMTestCase."""
    from deepeval.test_case import LLMTestCase

    context = extract_retrieval_context(stored.get("tool_calls_detail", []))
    return LLMTestCase(
        input=stored.get("query", ""),
        actual_output=stored.get("response_full", ""),
        retrieval_context=context,
        context=context,
    )


def build_metrics(*, category: str, judge_model: str) -> list:
    """Build the metric list for a given query category.

    Non-refuse categories receive 3 metrics; refuse adds a 4th GEval.
    """
    from deepeval.metrics import (
        AnswerRelevancyMetric,
        FaithfulnessMetric,
        GEval,
        HallucinationMetric,
    )
    from deepeval.test_case import LLMTestCaseParams

    metrics: list = [
        AnswerRelevancyMetric(threshold=ANSWER_RELEVANCY_THRESHOLD, model=judge_model),
        FaithfulnessMetric(threshold=FAITHFULNESS_THRESHOLD, model=judge_model),
        HallucinationMetric(threshold=HALLUCINATION_THRESHOLD, model=judge_model),
    ]

    if category == "refuse":
        metrics.append(
            GEval(
                name="Partial Refusal Quality",
                criteria=(
                    "Determine whether the response correctly handled a query mixing valid "
                    "and contradictory sub-questions: the valid part should be answered "
                    "using actual data, while the contradictory part should be explicitly "
                    "refused with a reason — not fabricated or silently ignored."
                ),
                evaluation_params=[
                    LLMTestCaseParams.INPUT,
                    LLMTestCaseParams.ACTUAL_OUTPUT,
                ],
                threshold=PARTIAL_REFUSAL_THRESHOLD,
                model=judge_model,
            )
        )

    return metrics


# Map DeepEval's metric.name → output JSON key. GEval inherits its name from
# the constructor argument; the three built-ins emit human-readable names.
_METRIC_NAME_TO_KEY = {
    "answer relevancy": "answer_relevancy",
    "faithfulness": "faithfulness",
    "hallucination": "hallucination",
    "partial refusal quality": "partial_refusal",
}


def _metric_key(name: str) -> str:
    return _METRIC_NAME_TO_KEY.get(name.strip().lower(), name.strip().lower().replace(" ", "_"))


def _metric_record(md: Any) -> dict[str, Any]:
    """Convert a DeepEval MetricData into our flat record shape.

    A metric whose score is None (typically because the judge LLM declined to
    respond — e.g. Gemini safety filters on CVE / vulnerability content) is
    recorded as a soft skip with `passed=None` so downstream summary logic
    can ignore it without treating it as a hard fail.
    """
    score = getattr(md, "score", None)
    error = getattr(md, "error", None)
    if score is None:
        return {
            "score": None,
            "passed": None,
            "reason": f"judge returned no score (error: {error})" if error else "judge returned no score",
        }
    return {
        "score": score,
        "passed": bool(md.success),
        "reason": getattr(md, "reason", None) or "",
    }


def _build_summary(results: list[dict[str, Any]]) -> dict[str, int]:
    structural_pass = sum(1 for r in results if r["structural_pass"])
    semantic_pass = sum(1 for r in results if r["semantic_pass"])
    both_pass = sum(1 for r in results if r["structural_pass"] and r["semantic_pass"])
    structural_only = sum(1 for r in results if r["structural_pass"] and not r["semantic_pass"])
    semantic_only = sum(1 for r in results if not r["structural_pass"] and r["semantic_pass"])
    both_fail = sum(1 for r in results if not r["structural_pass"] and not r["semantic_pass"])
    return {
        "structural_pass": structural_pass,
        "semantic_pass": semantic_pass,
        "both_pass": both_pass,
        "structural_only": structural_only,
        "semantic_only": semantic_only,
        "both_fail": both_fail,
    }


def judge_model_results(
    model_name: str,
    *,
    evaluate_fn: Callable | None = None,
) -> dict[str, Any]:
    """Read stored results for `model_name`, run semantic metrics, and return aggregated output."""
    if evaluate_fn is None:
        from deepeval import evaluate as _real_evaluate

        evaluate_fn = _real_evaluate

    from deepeval.evaluate.configs import AsyncConfig, CacheConfig, ErrorConfig

    async_cfg = AsyncConfig(run_async=True, max_concurrent=10)
    cache_cfg = CacheConfig(use_cache=True, write_cache=True)
    # Continue past per-metric failures (e.g. judge LLM returning None on
    # safety-filtered content) so a single bad call doesn't kill the run.
    error_cfg = ErrorConfig(ignore_errors=True, skip_on_missing_params=False)

    judge_model = get_judge_model()
    stored = read_stored_results(model_name)

    # DeepEval's `evaluate()` runs the same metric set against every test case in
    # one call. We have two metric sets (refuse vs non-refuse), so we group by
    # category and call evaluate once per group, then weave per-query records
    # back together preserving the original stored order.
    refuse_indices = [i for i, r in enumerate(stored) if r.get("category") == "refuse"]
    non_refuse_indices = [i for i, r in enumerate(stored) if r.get("category") != "refuse"]

    metric_data_by_index: dict[int, dict[str, Any]] = {}

    for indices, sample_category in (
        (non_refuse_indices, "discover"),
        (refuse_indices, "refuse"),
    ):
        if not indices:
            continue
        cases = [build_test_case(stored[i]) for i in indices]
        metrics = build_metrics(
            category=sample_category,
            judge_model=_build_judge_llm(judge_model),
        )
        eval_result = evaluate_fn(
            test_cases=cases,
            metrics=metrics,
            async_config=async_cfg,
            cache_config=cache_cfg,
            error_config=error_cfg,
        )
        for subset_idx, original_idx in enumerate(indices):
            test_result = eval_result.test_results[subset_idx]
            metric_data_by_index[original_idx] = {
                _metric_key(md.name): md for md in test_result.metrics_data
            }

    results: list[dict[str, Any]] = []
    for i, r in enumerate(stored):
        md_dict = metric_data_by_index.get(i, {})
        metrics_record: dict[str, dict[str, Any]] = {
            "answer_relevancy": _metric_record(md_dict["answer_relevancy"]),
            "faithfulness": _metric_record(md_dict["faithfulness"]),
            "hallucination": _metric_record(md_dict["hallucination"]),
        }
        if r.get("category") == "refuse" and "partial_refusal" in md_dict:
            metrics_record["partial_refusal"] = _metric_record(md_dict["partial_refusal"])
        else:
            metrics_record["partial_refusal"] = empty_partial_refusal_record()

        applicable = [m for m in metrics_record.values() if m["passed"] is not None]
        semantic_pass = bool(applicable) and all(m["passed"] for m in applicable)
        structural_pass = bool(r.get("judge_result", {}).get("pass_", False))

        results.append(
            {
                "query_id": r["query_id"],
                "structural_pass": structural_pass,
                "metrics": metrics_record,
                "semantic_pass": semantic_pass,
                "judge_disagreement": structural_pass != semantic_pass,
            }
        )

    return {
        "judge_model": judge_model,
        "model": model_name,
        "results": results,
        "summary": _build_summary(results),
    }


# --- CLI ---

import typer  # noqa: E402

app = typer.Typer(help="Semantic judge layer using DeepEval.")


# Module-level hook so tests can swap in a fake evaluate without touching
# `deepeval` for real. Production code falls through to `deepeval.evaluate`.
_default_evaluate: Callable | None = None


@app.command()
def main(
    model: str = typer.Option(..., "--model", help="Under-test model name (must match evals/results/{model}.json)"),
) -> None:
    """Run semantic judge on stored results for the given model."""
    output = judge_model_results(model, evaluate_fn=_default_evaluate)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{model}.json"
    output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"✓ Wrote {output_path}")
    typer.echo(f"  summary: {output['summary']}")


if __name__ == "__main__":
    app()
