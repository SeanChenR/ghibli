"""LiteLLM multi-model chat interface for ghibli eval pipeline."""

from __future__ import annotations

import json
import os
import re
import time

import litellm
from litellm.exceptions import APIConnectionError as LiteLLMConnectionError
from litellm.exceptions import RateLimitError as LiteLLMRateLimitError

import ghibli.tools as _tools
from ghibli.tool_schema import get_openai_tool_schemas
from ghibli.exceptions import ToolCallError

_OLLAMA_CLOUD_API_BASE = "https://ollama.com"

_MODEL_CONFIG: dict[str, dict] = {
    "gemini": {
        "model_id": "gemini/gemini-2.5-flash",
        "api_key_env": "GEMINI_API_KEY",
    },
    "gemma4": {
        "model_id": "gemini/gemma-4-26b-a4b-it",
        "api_key_env": "GEMINI_API_KEY",
    },
    "gpt4o-mini": {
        "model_id": "openai/gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    },
    "ollama-cloud": {
        # Model resolved at runtime from OLLAMA_CLOUD_MODEL env var (default: llama3.1:8b)
        "model_prefix": "ollama_chat/",
        "model_env": "OLLAMA_CLOUD_MODEL",
        "model_default": "llama3.1:8b",
        "api_key_env": "OLLAMA_API_KEY",
        "api_base": _OLLAMA_CLOUD_API_BASE,
    },
}

_SYSTEM_PROMPT = """\
You are ghibli, a GitHub assistant that answers questions using the GitHub API.
Today's date is 2026-04-22.

## Always use tools — never answer from training data
For any question about GitHub repositories, users, or statistics, ALWAYS call the \
appropriate tool to get live data. Never answer from memory or training knowledge alone. \
Years like 2024 and 2025 are in the past — always search for them.

## Typo correction
Before calling any tool, silently correct obvious typos in repository names, \
organization names, and programming language names. \
If you correct a repo name but the owner is unknown, call search_repositories \
first to find the correct owner, then call the originally requested tool.

## search_repositories — q is always required
The `q` parameter is mandatory for every call to search_repositories. \
Never call search_repositories() without q.
- For "most popular" / "best" queries with no specific keyword, use q="stars:>10000".
- For "interesting open source" queries, use q="stars:>1000 pushed:>2024-01-01".
- For "recent trending" / queries about a specific year (e.g. 2025), \
  use q="created:>YEAR-01-01 stars:>500 <keywords>" substituting the actual year and topic.
- For "good first issue" / beginner-friendly queries, use q="good-first-issues:>N language:LANG".

## Tool selection — critical rules
Each tool has a strict scope. Using the wrong tool is always incorrect:
- list_issues / list_pull_requests: ONLY for a SPECIFIC repo (requires owner + repo). \
  NEVER use for cross-repo searches.
- search_issues: For finding issues or PRs ACROSS multiple repos. \
  Use when no specific single repo is mentioned.
- get_repository: Returns repo metadata and primary language string only. \
  It does NOT return README content or a full language breakdown.
- get_languages: Use when the user wants the FULL language breakdown (bytes per language). \
  Do NOT substitute get_repository.
- get_readme: Use when the user wants to READ the README content. \
  get_repository does not include README text. Always prefer get_readme for README requests.
- list_contributors: Use to list contributors of a SPECIFIC repo (owner + repo required).
- search_users: Use to FIND developers, users, or organisations by criteria \
  (e.g. followers, location, language). Do NOT use search_repositories for finding people.
- list_commits: Use to see commit history of a SPECIFIC repo (owner + repo required).
- search_code: Use to find code PATTERNS or function calls across GitHub repos. \
  Do NOT use search_repositories when the user is asking about code content.

## Multi-step queries
When the user asks you to search for a repo AND THEN get details AND THEN list \
PRs/issues/releases — you MUST call ALL requested tools in sequence. \
After receiving each tool result, continue to the next requested step. \
Do not stop after the first tool call if more steps were requested.
Rules for calling get_repository in multi-step queries:
- If the user said "取得 repo 資訊", "repo 詳細資訊", "repo details", or "先取得它的資訊" \
  anywhere in the query, you MUST call get_repository even if you already know the owner/repo.
- Never skip get_repository just because you found the repo name via search_repositories.

## Contradictory or impossible conditions
When a query describes a physically or logically impossible condition, you MUST respond \
with an explanation only — never call any tool, not even to "verify" or "check". \
Impossible conditions include:
- Stars > 500,000 on any single repo (GitHub max is ~240k).
- Forks exceeding stars by 10× or more (forks are always much fewer than stars).
- A PR or issue that is simultaneously open AND closed.
- Repos created in future years (after 2026).
- Any other empirically impossible combination.
IMPORTANT: stars >> forks is COMPLETELY NORMAL (20:1 or even 100:1 ratio is common). \
Only forks >> stars (fork count much larger than stars) is impossible. \
If the query asks for repos where stars are 20× forks, call the tool normally.

## Language
Always reply in the same language the user wrote in.
"""


def _resolve_model_id(model_name: str, config: dict) -> str:
    """Resolve the LiteLLM model ID, supporting env-var-based dynamic model names."""
    if "model_env" in config:
        model = os.environ.get(config["model_env"], config["model_default"])
        return f"{config['model_prefix']}{model}"
    return config["model_id"]


def chat_with_model(
    user_message: str,
    session_id: str,
    model_name: str,
) -> tuple[str, list[str]]:
    """Run a query through the specified LLM using LiteLLM and return (reply, tools_called).

    Args:
        user_message: The natural language query from the user
        session_id: Session identifier (unused by LiteLLM path, kept for API parity)
        model_name: One of "gemini", "gemma4", "gpt4o-mini", "ollama-cloud"

    Returns:
        Tuple of (text response, list of tool names called)
    """
    if model_name not in _MODEL_CONFIG:
        valid = ", ".join(sorted(_MODEL_CONFIG))
        raise ToolCallError(
            f"Unknown model '{model_name}'. Valid options: {valid}"
        )

    config = _MODEL_CONFIG[model_name]
    api_key_env = config.get("api_key_env")
    if api_key_env and not os.environ.get(api_key_env):
        raise ToolCallError(
            f"Missing required environment variable: {api_key_env}"
        )

    model_id = _resolve_model_id(model_name, config)
    extra_body = config.get("extra_body", {})
    tools_called: list[str] = []
    tool_schemas = get_openai_tool_schemas()

    messages: list[dict] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]

    while True:
        try:
            kwargs: dict = {
                "model": model_id,
                "messages": messages,
                "tools": tool_schemas,
                "tool_choice": "auto",
                "timeout": 120,
            }
            if extra_body:
                kwargs["extra_body"] = extra_body
            if "api_base" in config:
                kwargs["api_base"] = config["api_base"]
                # Explicitly pass API key for providers with custom api_base
                if api_key_env and (key := os.environ.get(api_key_env)):
                    kwargs["api_key"] = key
            response = litellm.completion(**kwargs)
        except LiteLLMRateLimitError as e:
            m = re.search(r"try again in (\d+(?:\.\d+))s", str(e))
            wait = float(m.group(1)) + 2 if m else 20.0
            time.sleep(wait)
            continue
        except LiteLLMConnectionError as e:
            raise ToolCallError(f"Connection error: {e}") from e

        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            return msg.content or "", tools_called

        # Execute tool calls and feed results back
        messages.append({"role": "assistant", "content": msg.content, "tool_calls": msg.tool_calls})

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            fn_args = json.loads(tc.function.arguments)
            tools_called.append(fn_name)

            # Coerce string values to expected Python types
            fn = getattr(_tools, fn_name, None)
            if fn is not None:
                import inspect as _inspect
                for param_name, param in _inspect.signature(fn).parameters.items():
                    if param_name in fn_args and isinstance(fn_args[param_name], str):
                        annotation = param.annotation
                        if annotation is int or annotation == "int":
                            try:
                                fn_args[param_name] = int(fn_args[param_name])
                            except (ValueError, TypeError):
                                pass

            try:
                result = getattr(_tools, fn_name)(**fn_args)
            except Exception as e:
                result = {"error": str(e)}

            result_str = json.dumps(result, ensure_ascii=False, default=str)
            if len(result_str) > 4000:
                result_str = result_str[:4000] + "... [truncated]"
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result_str,
            })
